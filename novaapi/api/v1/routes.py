import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.api.deps import current_user, get_session, internal_only, refresh_prices
from novaapi.core.config import settings
from novaapi.models import Asset, Notification, SupportTicket, Transaction, User, Wallet, NotificationPreference, Watchlist
from novaapi.security.telegram import InitDataError, validate_init_data
from novaapi.security.tokens import create_token
from novaapi.services import transfer as tsvc
from novaapi.services import market
from novaapi.services import swap as swapsvc
from novaapi.services import wallet as wsvc

router = APIRouter(prefix="/api/v1")


class TgAuth(BaseModel):
    init_data: str


class TransferIn(BaseModel):
    recipient: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=12)
    amount: Decimal = Field(gt=0, max_digits=38, decimal_places=18)
    idempotency_key: str = Field(min_length=8, max_length=128)


def user_out(u: User) -> dict:
    return {"id": str(u.id), "telegram_id": u.telegram_id, "username": u.username, "first_name": u.first_name,
            "photo_url": u.photo_url, "language": u.language, "status": u.status, "registered_at": u.created_at.isoformat()}


def asset_out(a: Asset) -> dict:
    return {"symbol": a.symbol, "name": a.name, "description": a.description, "icon": a.icon, "category": a.category,
            "price": str(a.virtual_price), "total_supply": str(a.total_supply),
            "max_supply": str(a.max_supply) if a.max_supply is not None else None,
            "market_cap": str(a.total_supply * a.virtual_price), "is_demo": a.is_demo}


@router.post("/auth/telegram")
async def auth_telegram(body: TgAuth, s: AsyncSession = Depends(get_session)):
    try:
        tg = validate_init_data(body.init_data, settings.bot_token, settings.initdata_max_age_seconds)
    except InitDataError:
        raise HTTPException(401, "invalid initData")
    user, created = await wsvc.get_or_create_user(s, tg)
    await s.commit()
    return {"token": create_token(str(user.id), settings.secret_key, settings.session_ttl_seconds),
            "user": user_out(user), "created": created}


@router.get("/users/me")
async def me(u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    n = (await s.execute(select(func.count()).select_from(Transaction).join(Wallet, or_(
        Wallet.id == Transaction.from_wallet_id, Wallet.id == Transaction.to_wallet_id)).where(Wallet.user_id == u.id))).scalar_one()
    return {**user_out(u), "transactions": n}


class LangIn(BaseModel):
    language: str = Field(pattern="^(ru|en)$")


@router.put("/users/me/language")
async def set_language(b: LangIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    u.language = b.language
    await s.commit()
    return {"language": b.language}


@router.get("/users/lookup")
async def lookup(q: str = Query(min_length=1), u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    r = await tsvc.find_user(s, q)
    if not r or r.id == u.id:
        raise HTTPException(404, "recipient not found")
    return {"id": str(r.id), "username": r.username, "first_name": r.first_name}


@router.get("/wallets/me", dependencies=[Depends(refresh_prices)])
async def wallet_me(u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return await wsvc.portfolio(s, u)


@router.get("/portfolio", dependencies=[Depends(refresh_prices)])
async def portfolio(u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return await wsvc.portfolio(s, u)


@router.get("/assets", dependencies=[Depends(refresh_prices)])
async def assets(category: str | None = None, q: str | None = None, s: AsyncSession = Depends(get_session),
                 u: User = Depends(current_user)):
    st = select(Asset).where(Asset.is_active).order_by(Asset.symbol)
    watched = set((await s.execute(select(Watchlist.asset_id).where(Watchlist.user_id == u.id))).scalars())
    if category == "watchlist":
        st = st.where(Asset.id.in_(watched or {uuid.uuid4()}))
    elif category and category != "all":
        st = st.where(Asset.category == category)
    if q:
        st = st.where(or_(Asset.symbol.ilike(f"%{q}%"), Asset.name.ilike(f"%{q}%")))
    out = []
    for a in (await s.execute(st)).scalars():
        out.append({**asset_out(a), "change_24h": await market.change_pct(s, a), "watched": a.id in watched})
    return out


@router.get("/assets/{symbol}", dependencies=[Depends(refresh_prices)])
async def asset(symbol: str, s: AsyncSession = Depends(get_session), _: User = Depends(current_user)):
    a = (await s.execute(select(Asset).where(Asset.symbol == symbol.upper()))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    return {**asset_out(a), "change_24h": await market.change_pct(s, a)}


def tx_out(t: Transaction, my_wallet: uuid.UUID, a: Asset, users: dict) -> dict:
    direction = "sent" if t.from_wallet_id == my_wallet else "received"
    kind = t.type if t.type != "transfer" else direction
    return {"id": str(t.id), "type": kind, "direction": direction, "symbol": a.symbol, "amount": str(t.amount),
            "fee": str(t.fee), "from": users.get(t.from_wallet_id), "to": users.get(t.to_wallet_id),
            "status": t.status, "created_at": t.created_at.isoformat()}


@router.get("/transactions")
async def transactions(type: str | None = None, q: str | None = None, order: str = "desc", limit: int = 50, offset: int = 0,
                       u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    w = (await s.execute(select(Wallet).where(Wallet.user_id == u.id))).scalar_one()
    st = select(Transaction, Asset).join(Asset, Asset.id == Transaction.asset_id).where(
        or_(Transaction.from_wallet_id == w.id, Transaction.to_wallet_id == w.id))
    if type == "sent":
        st = st.where(Transaction.type == "transfer", Transaction.from_wallet_id == w.id)
    elif type == "received":
        st = st.where(or_(Transaction.type != "transfer", Transaction.to_wallet_id == w.id), Transaction.to_wallet_id == w.id)
    elif type == "swap":
        st = st.where(Transaction.type.in_(["swap_in", "swap_out"]))
    elif type in ("admin_credit", "admin_debit"):
        st = st.where(Transaction.type == type)
    elif type == "issuance":
        st = st.where(Transaction.type.in_(["issuance", "initial_grant"]))
    if q:
        st = st.where(or_(Asset.symbol.ilike(f"%{q}%"), Transaction.id.cast(str).ilike(f"%{q}%")))
    st = st.order_by(Transaction.created_at.asc() if order == "asc" else Transaction.created_at.desc()).limit(min(limit, 100)).offset(offset)
    rows = (await s.execute(st)).all()
    ids = {x for t, _ in rows for x in (t.from_wallet_id, t.to_wallet_id) if x}
    users = {w_.id: (un or "") for w_, un in (await s.execute(select(Wallet, User.username).join(User, User.id == Wallet.user_id).where(Wallet.id.in_(ids)))).all()} if ids else {}
    return [tx_out(t, w.id, a, users) for t, a in rows]


@router.post("/transfers")
async def make_transfer(body: TransferIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    try:
        tx = await tsvc.send(s, u, body.recipient, body.symbol, body.amount, f"{u.id}:{body.idempotency_key}")
    except tsvc.TransferError as e:
        raise HTTPException(400, {"code": e.code, "message": e.message})
    return {"id": str(tx.id), "status": tx.status, "amount": str(tx.amount), "fee": str(tx.fee)}


class PrefIn(BaseModel):
    transfers: bool
    announcements: bool


@router.put("/notifications/preferences")
async def set_prefs(body: PrefIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    p = (await s.execute(select(NotificationPreference).where(NotificationPreference.user_id == u.id))).scalar_one()
    p.transfers, p.announcements = body.transfers, body.announcements
    await s.commit()
    return body


class TicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


@router.post("/support")
async def support(body: TicketIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    t = SupportTicket(user_id=u.id, subject=body.subject, message=body.message)
    s.add(t); await s.commit()
    return {"id": str(t.id), "status": t.status}


@router.get("/assets/{symbol}/history", dependencies=[Depends(refresh_prices)])
async def asset_history(symbol: str, range: str = "24H", s: AsyncSession = Depends(get_session), _: User = Depends(current_user)):
    a = (await s.execute(select(Asset).where(Asset.symbol == symbol.upper()))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    return await market.history(s, a, range)


@router.get("/portfolio/history", dependencies=[Depends(refresh_prices)])
async def portfolio_hist(range: str = "24H", u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    return await market.portfolio_history(s, u.id, range)


@router.get("/config")
async def public_config(_: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    from novaapi.services.settings import transfer_cfg
    c = await transfer_cfg(s)
    from novaapi.services.settings import swap_cfg
    return {"fee_enabled": c["fee_enabled"], "fee_percent": str(c["fee_percent"]), "max_amount": str(c["max_amount"]),
            "daily_limit": str(c["daily_limit"]), "swap_fee_percent": str((await swap_cfg(s))["fee_percent"]), "demo": True}


class SwapIn(BaseModel):
    from_symbol: str = Field(min_length=1, max_length=12)
    to_symbol: str = Field(min_length=1, max_length=12)
    amount: Decimal = Field(gt=0, max_digits=38, decimal_places=18)
    min_receive: Decimal = Field(default=Decimal(0), ge=0, max_digits=38, decimal_places=18)
    idempotency_key: str = Field(min_length=8, max_length=128)


@router.get("/swap/quote", dependencies=[Depends(refresh_prices)])
async def swap_quote(from_symbol: str, to_symbol: str, amount: Decimal = Query(gt=0), _: User = Depends(current_user),
                     s: AsyncSession = Depends(get_session)):
    try:
        return await swapsvc.quote(s, from_symbol, to_symbol, amount)
    except swapsvc.SwapError as e:
        raise HTTPException(400, {"code": e.code, "message": e.message})


@router.post("/swap", dependencies=[Depends(refresh_prices)])
async def do_swap(b: SwapIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    try:
        return await swapsvc.execute(s, u, b.from_symbol, b.to_symbol, b.amount, b.min_receive, f"{u.id}:{b.idempotency_key}")
    except swapsvc.SwapError as e:
        raise HTTPException(409 if e.code == "price_changed" else 400, {"code": e.code, "message": e.message})


class WatchIn(BaseModel):
    watched: bool


@router.put("/watchlist/{symbol}")
async def watch(symbol: str, b: WatchIn, u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    a = (await s.execute(select(Asset).where(Asset.symbol == symbol.upper()))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    if b.watched:
        await s.execute(pg_insert(Watchlist).values(id=uuid.uuid4(), user_id=u.id, asset_id=a.id).on_conflict_do_nothing(index_elements=["user_id", "asset_id"]))
    else:
        await s.execute(delete(Watchlist).where(Watchlist.user_id == u.id, Watchlist.asset_id == a.id))
    await s.commit()
    return {"symbol": a.symbol, "watched": b.watched}


@router.get("/transactions/recipients")
async def recipients(u: User = Depends(current_user), s: AsyncSession = Depends(get_session)):
    """Last people you sent to (for quick re-send)."""
    w = (await s.execute(select(Wallet).where(Wallet.user_id == u.id))).scalar_one()
    last = func.max(Transaction.created_at)
    rows = (await s.execute(select(User.username, last).select_from(Transaction).join(Wallet, Wallet.id == Transaction.to_wallet_id)
                            .join(User, User.id == Wallet.user_id).where(Transaction.type == "transfer", Transaction.from_wallet_id == w.id, User.username.is_not(None))
                            .group_by(User.username).order_by(last.desc()).limit(6))).all()
    return [{"username": un} for un, _ in rows]


# ---------- internal API for the bot (shared secret) ----------
internal = APIRouter(prefix="/internal", dependencies=[Depends(internal_only)])


class BotStart(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None


@internal.post("/start")
async def bot_start(b: BotStart, s: AsyncSession = Depends(get_session)):
    user, created = await wsvc.get_or_create_user(s, b.model_dump())
    await s.commit()
    return {"created": created, "user": user_out(user)}


@internal.get("/summary/{telegram_id}")
async def bot_summary(telegram_id: int, s: AsyncSession = Depends(get_session)):
    u = (await s.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "not registered")
    w = await wsvc.portfolio(s, u)
    w_id = (await s.execute(select(Wallet.id).where(Wallet.user_id == u.id))).scalar_one()
    rows = (await s.execute(select(Transaction, Asset).join(Asset, Asset.id == Transaction.asset_id).where(
        or_(Transaction.from_wallet_id == w_id, Transaction.to_wallet_id == w_id)).order_by(Transaction.created_at.desc()).limit(10))).all()
    return {"user": user_out(u), "portfolio": w, "history": [
        {"type": t.type, "symbol": a.symbol, "amount": str(t.amount), "sign": "-" if t.from_wallet_id == w_id else "+",
         "at": t.created_at.isoformat()} for t, a in rows]}


@internal.get("/notifications/pending")
async def pending(s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(Notification, User.telegram_id).join(User, User.id == Notification.user_id)
                            .where(Notification.status == "pending").order_by(Notification.created_at).limit(50))).all()
    return [{"id": str(n.id), "telegram_id": tg, "type": n.type, "payload": n.payload} for n, tg in rows]


@internal.post("/notifications/{nid}/{result}")
async def mark(nid: uuid.UUID, result: str, s: AsyncSession = Depends(get_session)):
    if result not in ("sent", "failed"):
        raise HTTPException(400, "bad result")
    n = (await s.execute(select(Notification).where(Notification.id == nid))).scalar_one()
    n.status, n.sent_at = result, datetime.now(timezone.utc)
    await s.commit()
    return {"ok": True}
