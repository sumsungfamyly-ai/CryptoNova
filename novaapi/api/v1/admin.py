import csv, hmac, io, json, uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, distinct, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.api.admin_deps import COOKIE, Ctx, audit, client_ip, csrf_for, current_admin, require
from novaapi.api.deps import get_session
from novaapi.core.config import settings
from novaapi.models import (Admin, AdminLog, AdminRole, AdminSession, Asset, Balance, Notification, Setting, TokenIssuance,
                        Transaction, User, Wallet)
from novaapi.security.passwords import hash_password, new_totp_secret, verify_password, verify_totp
from novaapi.security.ratelimit import RateLimited, can_manage, limiter
from novaapi.security.tokens import create_token, decode_token
from novaapi.services import market, market_live as live, notifier, notify
from novaapi.services import ledger
from novaapi.services import wallet as wsvc

router = APIRouter(prefix="/api/v1/admin")
DUMMY = hash_password("dummy-password-for-timing")


class Reasoned(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirm: bool = False


def need_confirm(b: Reasoned):
    if not b.confirm:
        raise HTTPException(400, "confirmation required")


def s2(v):
    return None if v is None else str(v)


# ---------------- first-run setup (creates the OWNER in the browser) ----------------
async def _no_admins(s: AsyncSession) -> bool:
    return (await s.execute(select(func.count()).select_from(Admin))).scalar_one() == 0


@router.get("/setup/status")
async def setup_status(s: AsyncSession = Depends(get_session)):
    return {"needed": await _no_admins(s)}


class SetupStart(BaseModel):
    bot_token: str = Field(min_length=10, max_length=200)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    skip_mfa: bool = False  # explicit opt-out: sign in with the password only


@router.post("/setup/start")
async def setup_start(b: SetupStart, request: Request, s: AsyncSession = Depends(get_session)):
    """Step 1. Proof of ownership = knowing BOT_TOKEN (only the deployer has it). Returns a TOTP secret to add to an authenticator."""
    try:
        limiter.hit(f"setup:{client_ip(request)}", 5, 900)
    except RateLimited:
        raise HTTPException(429, "too many attempts, try later")
    if not await _no_admins(s):
        raise HTTPException(409, "owner already exists")
    if not settings.bot_token or not hmac.compare_digest(b.bot_token.strip().encode(), settings.bot_token.encode()):
        raise HTTPException(403, "wrong bot token")
    if b.skip_mfa:  # no authenticator: create the owner right away
        await s.execute(text("select pg_advisory_xact_lock(727003)"))
        if not await _no_admins(s):
            raise HTTPException(409, "owner already exists")
        role = (await s.execute(select(AdminRole).where(AdminRole.name == "OWNER"))).scalar_one()
        a = Admin(email=b.email.lower(), password_hash=hash_password(b.password), role_id=role.id, mfa_enabled=False)
        s.add(a); await s.flush()
        await audit(s, None, "owner_created_without_mfa", "admin", a.id, admin_id=a.id, ip=client_ip(request))
        await s.commit()
        return {"done": True}
    secret = new_totp_secret()
    email = b.email.lower()
    ticket = create_token(json.dumps({"e": email, "p": hash_password(b.password), "s": secret}), settings.secret_key, 900)
    return {"secret": secret, "otpauth": f"otpauth://totp/CryptoNOVA:{email}?secret={secret}&issuer=CryptoNOVA", "ticket": ticket}


class SetupFinish(BaseModel):
    ticket: str = Field(min_length=10, max_length=4000)
    code: str = Field(min_length=6, max_length=8)


@router.post("/setup/finish")
async def setup_finish(b: SetupFinish, request: Request, s: AsyncSession = Depends(get_session)):
    """Step 2. The owner is created only after a valid authenticator code (proves MFA is set up)."""
    try:
        limiter.hit(f"setupf:{client_ip(request)}", 10, 900)
    except RateLimited:
        raise HTTPException(429, "too many attempts, try later")
    sub = decode_token(b.ticket, settings.secret_key)
    if not sub:
        raise HTTPException(400, "session expired, start again")
    d = json.loads(sub)
    if not verify_totp(d["s"], b.code):
        raise HTTPException(400, "wrong code")
    await s.execute(text("select pg_advisory_xact_lock(727003)"))
    if not await _no_admins(s):
        raise HTTPException(409, "owner already exists")
    role = (await s.execute(select(AdminRole).where(AdminRole.name == "OWNER"))).scalar_one()
    a = Admin(email=d["e"], password_hash=d["p"], role_id=role.id, mfa_secret=d["s"], mfa_enabled=True)
    s.add(a); await s.flush()
    await audit(s, None, "owner_created", "admin", a.id, admin_id=a.id, ip=client_ip(request))
    await s.commit()
    return {"ok": True}


# ---------------- auth ----------------
class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    totp: str = ""


@router.post("/auth/login")
async def login(b: Login, request: Request, response: Response, s: AsyncSession = Depends(get_session)):
    ip = client_ip(request)
    try:
        limiter.hit(f"login-ip:{ip}", 20, 900); limiter.hit(f"login-em:{b.email.lower()}", 5, 900)
    except RateLimited:
        raise HTTPException(429, "too many attempts, try later")
    a = (await s.execute(select(Admin).where(func.lower(Admin.email) == b.email.lower()))).scalar_one_or_none()
    ok = verify_password(b.password, a.password_hash if a else DUMMY)
    role = (await s.execute(select(AdminRole).where(AdminRole.id == a.role_id))).scalar_one() if a else None
    if not (a and ok and a.status == "active"):
        await audit(s, None, "admin_login_failed", "admin", b.email.lower(), ip=ip); await s.commit()
        raise HTTPException(401, "invalid credentials")
    if a.mfa_enabled and not verify_totp(a.mfa_secret or "", b.totp):
        await audit(s, None, "admin_mfa_failed", "admin", a.id, admin_id=a.id, ip=ip); await s.commit()
        raise HTTPException(401, "invalid credentials")
    limiter.reset(f"login-em:{b.email.lower()}")
    sess = AdminSession(admin_id=a.id, ip_address=ip, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.admin_session_ttl_minutes))
    s.add(sess); a.last_login_at = datetime.now(timezone.utc); await s.flush()
    await audit(s, None, "admin_login", "admin", a.id, admin_id=a.id, ip=ip); await s.commit()
    response.set_cookie(COOKIE, create_token(str(sess.id), settings.secret_key, settings.admin_session_ttl_minutes * 60), httponly=True,
                        secure=settings.cookie_secure, samesite="strict", max_age=settings.admin_session_ttl_minutes * 60, path="/")
    return {"csrf": csrf_for(str(sess.id)), "email": a.email, "role": role.name}


@router.post("/auth/logout")
async def logout(response: Response, ctx: Ctx = Depends(current_admin), s: AsyncSession = Depends(get_session)):
    sess = (await s.execute(select(AdminSession).where(AdminSession.id == uuid.UUID(ctx.session_id)))).scalar_one()
    sess.revoked = True; await s.commit(); response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(ctx: Ctx = Depends(current_admin)):
    return {"email": ctx.admin.email, "role": ctx.role.name, "permissions": sorted(ctx.perms), "csrf": csrf_for(ctx.session_id)}


# ---------------- dashboard ----------------
def since_for(rng: str):
    now = datetime.now(timezone.utc)
    return {"today": now.replace(hour=0, minute=0, second=0, microsecond=0), "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30), "90d": now - timedelta(days=90)}.get(rng)


@router.get("/dashboard")
async def dashboard(range: str = "7d", ctx: Ctx = Depends(require("dashboard.view")), s: AsyncSession = Depends(get_session)):
    since = since_for(range)
    real_u = User.is_system.is_(False)
    one = lambda q: s.execute(q)
    total_users = (await one(select(func.count()).select_from(User).where(real_u))).scalar_one()
    total_wallets = (await one(select(func.count()).select_from(Wallet).join(User, User.id == Wallet.user_id).where(real_u))).scalar_one()
    total_tx = (await one(select(func.count()).select_from(Transaction))).scalar_one()
    tf = [Transaction.type == "transfer"] + ([Transaction.created_at >= since] if since else [])
    active = (await one(select(func.count(distinct(Transaction.from_wallet_id))).where(*tf))).scalar_one()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_transfers = (await one(select(func.count()).select_from(Transaction).where(Transaction.type == "transfer", Transaction.created_at >= today))).scalar_one()
    new_regs = (await one(select(func.count()).select_from(User).where(real_u, *([User.created_at >= since] if since else [])))).scalar_one()
    volume = (await one(select(func.coalesce(func.sum(Transaction.amount * Asset.virtual_price), 0)).join(Asset, Asset.id == Transaction.asset_id).where(*tf))).scalar_one()
    day = func.date_trunc("day", Transaction.created_at)
    tx_series = (await one(select(day, func.count(), func.coalesce(func.sum(Transaction.amount * Asset.virtual_price), 0))
                           .join(Asset, Asset.id == Transaction.asset_id).where(*([Transaction.created_at >= since] if since else []))
                           .group_by(day).order_by(day))).all()
    uday = func.date_trunc("day", User.created_at)
    user_series = (await one(select(uday, func.count()).where(real_u, *([User.created_at >= since] if since else [])).group_by(uday).order_by(uday))).all()
    dist = (await one(select(Asset.symbol, func.coalesce(func.sum(Balance.amount), 0), func.coalesce(func.sum(Balance.amount * Asset.virtual_price), 0))
                      .select_from(Asset).outerjoin(Balance, Balance.asset_id == Asset.id).outerjoin(Wallet, Wallet.id == Balance.wallet_id)
                      .outerjoin(User, User.id == Wallet.user_id).where(or_(User.id.is_(None), real_u)).group_by(Asset.symbol).order_by(Asset.symbol))).all()
    supply = (await one(select(Asset.symbol, Asset.total_supply, Asset.total_supply * Asset.virtual_price).order_by(Asset.symbol))).all()
    return {"demo": True, "range": range, "total_users": total_users, "active_users": active, "total_wallets": total_wallets,
            "total_transactions": total_tx, "daily_transfers": daily_transfers, "new_registrations": new_regs,
            "transaction_volume": str(volume), "total_virtual_supply": str(sum((r[2] for r in supply), Decimal(0))),
            "user_growth": [{"d": d.date().isoformat(), "v": n} for d, n in user_series],
            "transaction_activity": [{"d": d.date().isoformat(), "count": n, "volume": str(v)} for d, n, v in tx_series],
            "asset_distribution": [{"symbol": a, "amount": str(m), "value": str(v)} for a, m, v in dist],
            "virtual_supply": [{"symbol": a, "supply": str(m), "value": str(v)} for a, m, v in supply]}


# ---------------- users ----------------
bal_sub = (select(func.coalesce(func.sum(Balance.amount * Asset.virtual_price), 0)).select_from(Balance)
           .join(Asset, Asset.id == Balance.asset_id).join(Wallet, Wallet.id == Balance.wallet_id)
           .where(Wallet.user_id == User.id).correlate(User).scalar_subquery())
tx_sub = (select(func.count()).select_from(Transaction).join(Wallet, or_(Wallet.id == Transaction.from_wallet_id, Wallet.id == Transaction.to_wallet_id))
          .where(Wallet.user_id == User.id).correlate(User).scalar_subquery())


def user_row(u, bal, n):
    return {"id": str(u.id), "username": u.username, "first_name": u.first_name, "photo_url": u.photo_url, "telegram_id": u.telegram_id,
            "registered_at": u.created_at.isoformat(), "total_balance": str(bal), "transactions": n, "status": u.status, "note": u.admin_note}


@router.get("/users")
async def users(q: str = "", status: str = "", sort: str = "created_at", order: str = "desc", limit: int = 50, offset: int = 0,
                ctx: Ctx = Depends(require("users.view")), s: AsyncSession = Depends(get_session)):
    st = select(User, bal_sub.label("bal"), tx_sub.label("n")).where(User.is_system.is_(False))
    if q:
        st = st.where(or_(User.username.ilike(f"%{q}%"), User.first_name.ilike(f"%{q}%"), User.id.cast(str).ilike(f"%{q}%"), User.telegram_id.cast(str) == q))
    if status:
        st = st.where(User.status == status)
    col = {"created_at": User.created_at, "username": User.username, "balance": bal_sub, "transactions": tx_sub}.get(sort, User.created_at)
    st = st.order_by(col.asc() if order == "asc" else col.desc()).limit(min(limit, 200)).offset(offset)
    return [user_row(u, b, n) for u, b, n in (await s.execute(st)).all()]


@router.get("/users/{uid}")
async def user_detail(uid: uuid.UUID, ctx: Ctx = Depends(require("users.view")), s: AsyncSession = Depends(get_session)):
    r = (await s.execute(select(User, bal_sub, tx_sub).where(User.id == uid))).first()
    if not r:
        raise HTTPException(404, "user not found")
    w = (await s.execute(select(Wallet).where(Wallet.user_id == uid))).scalar_one()
    bals = (await s.execute(select(Asset.symbol, Balance.amount).join(Asset, Asset.id == Balance.asset_id).where(Balance.wallet_id == w.id))).all()
    txs = (await s.execute(select(Transaction, Asset.symbol).join(Asset, Asset.id == Transaction.asset_id)
                           .where(or_(Transaction.from_wallet_id == w.id, Transaction.to_wallet_id == w.id)).order_by(Transaction.created_at.desc()).limit(30))).all()
    return {**user_row(*r), "wallet": {"id": str(w.id), "public_id": w.public_id, "status": w.status},
            "balances": [{"symbol": a, "amount": str(m)} for a, m in bals],
            "history": [{"id": str(t.id), "type": t.type, "symbol": sym, "amount": str(t.amount), "status": t.status, "created_at": t.created_at.isoformat()} for t, sym in txs]}


class UserAction(Reasoned):
    pass


async def set_user_status(uid, new, b, ctx, s):
    need_confirm(b)
    u = (await s.execute(select(User).where(User.id == uid, User.is_system.is_(False)))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "user not found")
    prev = u.status; u.status = new
    await audit(s, ctx, f"user_{new}", "user", u.id, {"status": prev}, {"status": new}, b.reason)
    if new == "blocked":
        await notify.enqueue(s, u.id, "account_restricted", {}, f"restricted:{u.id}:{uuid.uuid4()}", critical=True)
    await s.commit()
    if new == "blocked":
        try:
            await notifier.deliver(s, limit=5, user_ids=[u.id])
        except Exception:
            pass
    return {"id": str(u.id), "status": new}


@router.post("/users/{uid}/block")
async def block(uid: uuid.UUID, b: UserAction, ctx: Ctx = Depends(require("users.block")), s: AsyncSession = Depends(get_session)):
    return await set_user_status(uid, "blocked", b, ctx, s)


@router.post("/users/{uid}/unblock")
async def unblock(uid: uuid.UUID, b: UserAction, ctx: Ctx = Depends(require("users.block")), s: AsyncSession = Depends(get_session)):
    return await set_user_status(uid, "active", b, ctx, s)


class Note(BaseModel):
    note: str = Field(max_length=2000)


@router.put("/users/{uid}/note")
async def note(uid: uuid.UUID, b: Note, ctx: Ctx = Depends(require("users.note")), s: AsyncSession = Depends(get_session)):
    u = (await s.execute(select(User).where(User.id == uid))).scalar_one_or_none()
    if not u:
        raise HTTPException(404, "user not found")
    await audit(s, ctx, "user_note", "user", u.id, {"note": u.admin_note}, {"note": b.note}, "note updated")
    u.admin_note = b.note; await s.commit()
    return {"ok": True}


# ---------------- wallets ----------------
@router.get("/wallets")
async def wallets(q: str = "", limit: int = 50, offset: int = 0, ctx: Ctx = Depends(require("wallets.view")), s: AsyncSession = Depends(get_session)):
    st = select(Wallet, User, bal_sub.label("bal")).join(User, User.id == Wallet.user_id).where(User.is_system.is_(False))
    if q:
        st = st.where(or_(Wallet.public_id.ilike(f"%{q}%"), User.username.ilike(f"%{q}%")))
    rows = (await s.execute(st.order_by(Wallet.created_at.desc()).limit(min(limit, 200)).offset(offset))).all()
    return [{"id": str(w.id), "public_id": w.public_id, "status": w.status, "username": u.username, "user_id": str(u.id), "total_balance": str(b)} for w, u, b in rows]


class Adjust(Reasoned):
    symbol: str
    amount: Decimal = Field(gt=0, max_digits=38, decimal_places=18)
    direction: str = Field(pattern="^(credit|debit)$")


@router.post("/wallets/{wid}/adjust")
async def adjust(wid: uuid.UUID, b: Adjust, ctx: Ctx = Depends(require("wallets.adjust")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    w = (await s.execute(select(Wallet).where(Wallet.id == wid))).scalar_one_or_none()
    a = (await s.execute(select(Asset).where(Asset.symbol == b.symbol.upper()))).scalar_one_or_none()
    if not w or not a:
        raise HTTPException(404, "wallet or asset not found")
    try:
        if b.direction == "credit":
            if a.max_supply is not None and a.total_supply + b.amount > a.max_supply:
                raise HTTPException(400, "max supply exceeded")
            tx = await wsvc.mint(s, w.id, a, b.amount, "admin_credit", b.reason, ctx.admin.id)
        else:
            tx = await wsvc.burn(s, w.id, a, b.amount, b.reason, ctx.admin.id)
        await audit(s, ctx, f"wallet_{b.direction}", "wallet", w.id, None, {"symbol": a.symbol, "amount": str(b.amount), "tx": str(tx.id)}, b.reason)
        await s.commit()
    except ledger.InsufficientFunds:
        await s.rollback(); raise HTTPException(400, "insufficient balance")
    except IntegrityError:
        await s.rollback(); raise HTTPException(400, "operation violates supply limits")
    return {"transaction_id": str(tx.id)}


async def set_wallet(wid, new, b, ctx, s):
    need_confirm(b)
    w = (await s.execute(select(Wallet).where(Wallet.id == wid))).scalar_one_or_none()
    if not w:
        raise HTTPException(404, "wallet not found")
    prev = w.status; w.status = new
    await audit(s, ctx, f"wallet_{'frozen' if new == 'frozen' else 'unfrozen'}", "wallet", w.id, {"status": prev}, {"status": new}, b.reason)
    await s.commit()
    return {"id": str(w.id), "status": new}


@router.post("/wallets/{wid}/freeze")
async def freeze(wid: uuid.UUID, b: Reasoned, ctx: Ctx = Depends(require("wallets.freeze")), s: AsyncSession = Depends(get_session)):
    return await set_wallet(wid, "frozen", b, ctx, s)


@router.post("/wallets/{wid}/unfreeze")
async def unfreeze(wid: uuid.UUID, b: Reasoned, ctx: Ctx = Depends(require("wallets.freeze")), s: AsyncSession = Depends(get_session)):
    return await set_wallet(wid, "active", b, ctx, s)


# ---------------- assets / issuance ----------------
def a_out(a: Asset):
    return {"id": str(a.id), "symbol": a.symbol, "name": a.name, "description": a.description, "icon": a.icon, "category": a.category,
            "price": str(a.virtual_price), "total_supply": str(a.total_supply), "max_supply": s2(a.max_supply), "is_active": a.is_active, "is_demo": a.is_demo}


@router.get("/assets")
async def assets(ctx: Ctx = Depends(require("assets.view")), s: AsyncSession = Depends(get_session)):
    return [a_out(a) for a in (await s.execute(select(Asset).order_by(Asset.symbol))).scalars()]


class NewAsset(Reasoned):
    symbol: str = Field(pattern="^[A-Z0-9]{2,12}$")
    name: str = Field(min_length=2, max_length=64)
    description: str = ""
    icon: str | None = None
    category: str = Field(default="nova", pattern="^(popular|stable|nova)$")
    virtual_price: Decimal = Field(ge=0, max_digits=38, decimal_places=18)
    max_supply: Decimal | None = Field(default=None, gt=0, max_digits=38, decimal_places=18)
    decimal_precision: int = Field(default=8, ge=0, le=18)


@router.post("/assets")
async def create_asset(b: NewAsset, ctx: Ctx = Depends(require("assets.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    if (await s.execute(select(Asset).where(Asset.symbol == b.symbol))).scalar_one_or_none():
        raise HTTPException(409, "symbol already exists")
    a = Asset(symbol=b.symbol, name=b.name, description=b.description, icon=b.icon, category=b.category, virtual_price=b.virtual_price,
              max_supply=b.max_supply, decimal_precision=b.decimal_precision)
    s.add(a); await s.flush(); await market.record_price(s, a)
    await live.set_anchor(s, a.symbol, a.virtual_price)
    await audit(s, ctx, "asset_created", "asset", a.id, None, a_out(a), b.reason)
    for uid in (await s.execute(select(User.id).where(User.is_system.is_(False), User.status == "active"))).scalars():
        await notify.enqueue(s, uid, "asset_created", {"symbol": a.symbol}, f"asset_created:{a.id}:{uid}")
    await s.commit()
    return a_out(a)


class EditAsset(Reasoned):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    virtual_price: Decimal | None = Field(default=None, ge=0, max_digits=38, decimal_places=18)
    max_supply: Decimal | None = Field(default=None, gt=0, max_digits=38, decimal_places=18)
    is_active: bool | None = None


@router.put("/assets/{symbol}")
async def edit_asset(symbol: str, b: EditAsset, ctx: Ctx = Depends(require("assets.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    a = (await s.execute(select(Asset).where(Asset.symbol == symbol.upper()))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "asset not found")
    prev = a_out(a)
    if b.max_supply is not None and b.max_supply < a.total_supply:
        raise HTTPException(400, "max supply below current supply")
    for f in ("name", "description", "icon", "max_supply", "is_active"):
        v = getattr(b, f)
        if v is not None:
            setattr(a, f, v)
    if b.virtual_price is not None and b.virtual_price != a.virtual_price:
        a.virtual_price = b.virtual_price; await market.record_price(s, a)
        await live.set_anchor(s, a.symbol, a.virtual_price)
        await audit(s, ctx, "asset_price_changed", "asset", a.id, {"price": prev["price"]}, {"price": str(b.virtual_price)}, b.reason)
    await audit(s, ctx, "asset_updated", "asset", a.id, prev, a_out(a), b.reason)
    await s.commit()
    return a_out(a)


@router.get("/assets/{symbol}/distribution")
async def distribution(symbol: str, ctx: Ctx = Depends(require("assets.view")), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(User.username, Wallet.public_id, Balance.amount).join(Wallet, Wallet.id == Balance.wallet_id)
                            .join(User, User.id == Wallet.user_id).join(Asset, Asset.id == Balance.asset_id)
                            .where(Asset.symbol == symbol.upper(), User.is_system.is_(False), Balance.amount > 0).order_by(Balance.amount.desc()).limit(100))).all()
    return [{"username": u, "wallet": w, "amount": str(m)} for u, w, m in rows]


class Issue(Reasoned):
    symbol: str
    wallet: str  # wallet UUID or public id (NW-...)
    amount: Decimal = Field(gt=0, max_digits=38, decimal_places=18)


@router.post("/issuance")
async def issue(b: Issue, ctx: Ctx = Depends(require("issuance.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    a = (await s.execute(select(Asset).where(Asset.symbol == b.symbol.upper()))).scalar_one_or_none()
    cond = Wallet.public_id == b.wallet.upper()
    try:
        cond = Wallet.id == uuid.UUID(b.wallet)
    except ValueError:
        pass
    w = (await s.execute(select(Wallet).where(cond))).scalar_one_or_none()
    if not a or not w:
        raise HTTPException(404, "wallet or asset not found")
    if a.max_supply is not None and a.total_supply + b.amount > a.max_supply:
        raise HTTPException(400, "max supply exceeded")
    try:
        tx = await wsvc.mint(s, w.id, a, b.amount, "issuance", b.reason, ctx.admin.id)
        s.add(TokenIssuance(asset_id=a.id, transaction_id=tx.id, admin_id=ctx.admin.id, amount=b.amount, reason=b.reason))
        await audit(s, ctx, "token_issued", "asset", a.id, None, {"amount": str(b.amount), "wallet": w.public_id, "tx": str(tx.id)}, b.reason)
        await s.commit()
    except IntegrityError:
        await s.rollback(); raise HTTPException(400, "max supply exceeded")
    return {"transaction_id": str(tx.id)}


@router.get("/issuance")
async def issuance_history(ctx: Ctx = Depends(require("issuance.manage")), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(TokenIssuance, Asset.symbol, Admin.email).join(Asset, Asset.id == TokenIssuance.asset_id)
                            .join(Admin, Admin.id == TokenIssuance.admin_id).order_by(TokenIssuance.created_at.desc()).limit(200))).all()
    return [{"id": str(i.id), "symbol": sym, "amount": str(i.amount), "admin": em, "reason": i.reason, "created_at": i.created_at.isoformat()} for i, sym, em in rows]


# ---------------- transactions ----------------
@router.get("/transactions")
async def all_tx(type: str = "", status: str = "", q: str = "", limit: int = 100, offset: int = 0,
                 ctx: Ctx = Depends(require("transactions.view")), s: AsyncSession = Depends(get_session)):
    st = select(Transaction, Asset.symbol).join(Asset, Asset.id == Transaction.asset_id)
    if type:
        st = st.where(Transaction.type == type)
    if status:
        st = st.where(Transaction.status == status)
    if q:
        st = st.where(or_(Asset.symbol.ilike(f"%{q}%"), Transaction.id.cast(str).ilike(f"%{q}%")))
    rows = (await s.execute(st.order_by(Transaction.created_at.desc()).limit(min(limit, 200)).offset(offset))).all()
    wids = {x for t, _ in rows for x in (t.from_wallet_id, t.to_wallet_id) if x}
    names = {w: p for w, p in (await s.execute(select(Wallet.id, Wallet.public_id).where(Wallet.id.in_(wids)))).all()} if wids else {}
    return [{"id": str(t.id), "type": t.type, "status": t.status, "symbol": sym, "amount": str(t.amount), "fee": str(t.fee),
             "from": names.get(t.from_wallet_id), "to": names.get(t.to_wallet_id), "reason": t.reason, "created_at": t.created_at.isoformat()} for t, sym in rows]


# ---------------- administrators ----------------
class NewAdmin(Reasoned):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: str


@router.get("/admins")
async def admins(ctx: Ctx = Depends(require("admins.manage")), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(Admin, AdminRole.name).join(AdminRole, AdminRole.id == Admin.role_id).order_by(Admin.created_at))).all()
    return [{"id": str(a.id), "email": a.email, "role": r, "status": a.status, "mfa": a.mfa_enabled, "last_login": s2(a.last_login_at)} for a, r in rows]


@router.post("/admins")
async def create_admin(b: NewAdmin, ctx: Ctx = Depends(require("admins.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    role = (await s.execute(select(AdminRole).where(AdminRole.name == b.role))).scalar_one_or_none()
    if not role or not can_manage(ctx.role.rank, role.rank + 1, role.rank):
        raise HTTPException(403, "cannot grant this role")
    if (await s.execute(select(Admin).where(func.lower(Admin.email) == b.email.lower()))).scalar_one_or_none():
        raise HTTPException(409, "email already used")
    secret = new_totp_secret()
    a = Admin(email=b.email.lower(), password_hash=hash_password(b.password), role_id=role.id, mfa_secret=secret, mfa_enabled=True)
    s.add(a); await s.flush()
    await audit(s, ctx, "admin_created", "admin", a.id, None, {"email": a.email, "role": role.name}, b.reason)
    await s.commit()
    return {"id": str(a.id), "totp_secret": secret, "otpauth": f"otpauth://totp/CryptoNOVA:{a.email}?secret={secret}&issuer=CryptoNOVA"}


class EditAdmin(Reasoned):
    role: str | None = None
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


@router.put("/admins/{aid}")
async def edit_admin(aid: uuid.UUID, b: EditAdmin, ctx: Ctx = Depends(require("admins.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    if aid == ctx.admin.id:
        raise HTTPException(403, "cannot modify your own permissions")
    a = (await s.execute(select(Admin).where(Admin.id == aid))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "admin not found")
    cur = (await s.execute(select(AdminRole).where(AdminRole.id == a.role_id))).scalar_one()
    new_role = (await s.execute(select(AdminRole).where(AdminRole.name == b.role))).scalar_one_or_none() if b.role else None
    if b.role and not new_role:
        raise HTTPException(404, "role not found")
    if not can_manage(ctx.role.rank, cur.rank, new_role.rank if new_role else None):
        raise HTTPException(403, "insufficient rank")
    prev = {"role": cur.name, "status": a.status}
    if new_role:
        a.role_id = new_role.id
    if b.status:
        a.status = b.status
    await audit(s, ctx, "admin_changed", "admin", a.id, prev, {"role": new_role.name if new_role else cur.name, "status": a.status}, b.reason)
    await s.commit()
    return {"ok": True}


# ---------------- logs / settings / notifications ----------------
@router.get("/logs")
async def logs(action: str = "", limit: int = 100, offset: int = 0, ctx: Ctx = Depends(require("logs.view")), s: AsyncSession = Depends(get_session)):
    st = select(AdminLog, Admin.email).outerjoin(Admin, Admin.id == AdminLog.admin_id)
    if action:
        st = st.where(AdminLog.action == action)
    rows = (await s.execute(st.order_by(AdminLog.created_at.desc()).limit(min(limit, 500)).offset(offset))).all()
    return [{"id": str(l.id), "admin": em, "action": l.action, "target": f"{l.target_type or ''}:{l.target_id or ''}", "previous": l.previous_value,
             "new": l.new_value, "reason": l.reason, "ip": l.ip_address, "at": l.created_at.isoformat()} for l, em in rows]


ALLOWED_SETTINGS = {"transfer_fee", "transfer_max_amount", "daily_limit", "swap_fee", "simulator_mode"}


@router.get("/settings")
async def get_settings(ctx: Ctx = Depends(require("settings.manage")), s: AsyncSession = Depends(get_session)):
    return {r.key: r.value for r in (await s.execute(select(Setting))).scalars()}


class SetIn(Reasoned):
    key: str
    value: dict


@router.put("/settings")
async def put_settings(b: SetIn, ctx: Ctx = Depends(require("settings.manage")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    if b.key not in ALLOWED_SETTINGS:
        raise HTTPException(400, "unknown setting")
    row = (await s.execute(select(Setting).where(Setting.key == b.key))).scalar_one_or_none()
    prev = row.value if row else None
    if row:
        row.value = b.value
    else:
        s.add(Setting(key=b.key, value=b.value))
    await audit(s, ctx, "settings_changed", "setting", b.key, prev, b.value, b.reason)
    await s.commit()
    return {"ok": True}


class Announce(Reasoned):
    text: str = Field(min_length=1, max_length=1000)
    kind: str = Field(default="announcement", pattern="^(announcement|maintenance)$")


@router.post("/notifications/announce")
async def announce(b: Announce, ctx: Ctx = Depends(require("notifications.send")), s: AsyncSession = Depends(get_session)):
    need_confirm(b)
    ntype, crit = ("system_maintenance", True) if b.kind == "maintenance" else ("admin_announcement", False)
    batch = uuid.uuid4(); n = 0
    for uid in (await s.execute(select(User.id).where(User.is_system.is_(False), User.status == "active"))).scalars():
        await notify.enqueue(s, uid, ntype, {"text": b.text}, f"announce:{batch}:{uid}", critical=crit); n += 1
    await audit(s, ctx, "announcement_sent", "notification", batch, None, {"kind": b.kind, "recipients": n}, b.reason)
    await s.commit()
    return {"queued": n}


@router.get("/notifications")
async def notifications(ctx: Ctx = Depends(require("notifications.send")), s: AsyncSession = Depends(get_session)):
    rows = (await s.execute(select(Notification.status, func.count()).group_by(Notification.status))).all()
    return {"by_status": {k: v for k, v in rows}}


@router.post("/notifications/flush")
async def flush(ctx: Ctx = Depends(require("notifications.send")), s: AsyncSession = Depends(get_session)):
    """Deliver up to 25 pending notifications per call; the panel calls it until remaining == 0."""
    return await notifier.deliver(s, limit=25)


def _safe(v) -> str:
    v = "" if v is None else str(v)
    return "'" + v if v and v[0] in "=+-@\t\r" else v  # CSV/Excel formula-injection guard


@router.get("/transactions/export.csv")
async def export_transactions(type: str = "", status: str = "", q: str = "", ctx: Ctx = Depends(require("transactions.view")),
                              s: AsyncSession = Depends(get_session)):
    rows = []
    for off in range(0, 10000, 200):
        page = await all_tx(type=type, status=status, q=q, limit=200, offset=off, ctx=ctx, s=s)
        rows += page
        if len(page) < 200:
            break
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["id", "type", "status", "asset", "amount", "fee", "from_wallet", "to_wallet", "reason", "created_at"])
    for r in rows:
        w.writerow([_safe(r[k]) for k in ("id", "type", "status", "symbol", "amount", "fee", "from", "to", "reason", "created_at")])
    await audit(s, ctx, "transactions_exported", "transaction", None, None, {"rows": len(rows), "filters": {"type": type, "status": status, "q": q}}, "CSV export")
    await s.commit()
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cryptonova_transactions.csv"})
