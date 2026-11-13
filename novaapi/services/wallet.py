import secrets, uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings
from novaapi.models import Asset, Balance, Transaction, User, Wallet, NotificationPreference
from novaapi.services import ledger, notify

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


async def treasury_wallet(s: AsyncSession) -> Wallet:
    return (await s.execute(select(Wallet).join(User, User.id == Wallet.user_id).where(User.is_system))).scalar_one()


async def mint(s: AsyncSession, wallet_id, asset: Asset, amount: Decimal, tx_type: str, reason: str,
               admin_id=None, key: str | None = None) -> Transaction:
    """Creates virtual units: treasury -amount, wallet +amount; raises supply (DB enforces max_supply)."""
    t = await treasury_wallet(s)
    await s.execute(pg_insert(Balance).values(id=uuid.uuid4(), wallet_id=t.id, asset_id=asset.id, amount=0, allow_negative=True)
                    .on_conflict_do_nothing(index_elements=["wallet_id", "asset_id"]))  # treasury row for assets created after seed
    tx = Transaction(type=tx_type, asset_id=asset.id, amount=amount, from_wallet_id=t.id, to_wallet_id=wallet_id,
                     reason=reason, initiated_by_admin_id=admin_id, idempotency_key=key)
    s.add(tx); await s.flush()
    await ledger.post_legs(s, tx.id, [(t.id, asset.id, -amount), (wallet_id, asset.id, amount)])
    asset.total_supply = asset.total_supply + amount
    await s.flush()
    return tx


async def get_or_create_user(s: AsyncSession, tg: dict) -> tuple[User, bool]:
    tid = int(tg["id"])
    user = (await s.execute(select(User).where(User.telegram_id == tid))).scalar_one_or_none()
    if user:
        user.username = tg.get("username") or user.username
        user.first_name = tg.get("first_name") or user.first_name
        user.photo_url = tg.get("photo_url") or user.photo_url
        await s.flush()
        return user, False
    user = User(telegram_id=tid, username=tg.get("username"), first_name=tg.get("first_name"),
                photo_url=tg.get("photo_url"))
    s.add(user); await s.flush()
    wallet = Wallet(user_id=user.id, public_id="NW-" + "".join(secrets.choice(ALPHABET) for _ in range(10)))
    s.add_all([wallet, NotificationPreference(user_id=user.id)]); await s.flush()
    for sym, amt in settings.parsed_starting_balances().items():
        a = (await s.execute(select(Asset).where(Asset.symbol == sym, Asset.is_active))).scalar_one_or_none()
        if a and amt > 0:
            await mint(s, wallet.id, a, amt, "initial_grant", "Starting balance (DEMO)", key=f"grant:{user.id}:{sym}")
    await notify.enqueue(s, user.id, "wallet_created", {"wallet_id": wallet.public_id}, f"wallet_created:{user.id}")
    return user, True


async def portfolio(s: AsyncSession, user: User) -> dict:
    w = (await s.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
    rows = (await s.execute(select(Balance, Asset).join(Asset, Asset.id == Balance.asset_id)
                            .where(Balance.wallet_id == w.id).order_by(Asset.symbol))).all()
    items = [{"symbol": a.symbol, "name": a.name, "amount": str(b.amount), "price": str(a.virtual_price),
              "value": str(b.amount * a.virtual_price), "icon": a.icon} for b, a in rows]
    return {"wallet_id": w.public_id, "wallet_status": w.status, "demo": True,
            "total_value": str(sum((Decimal(i["value"]) for i in items), Decimal(0))), "assets": items}


async def burn(s: AsyncSession, wallet_id, asset: Asset, amount: Decimal, reason: str, admin_id=None,
               tx_type: str = "admin_debit", key: str | None = None) -> Transaction:
    """Admin debit: wallet -amount, treasury +amount; reduces circulating supply."""
    t = await treasury_wallet(s)
    tx = Transaction(type=tx_type, asset_id=asset.id, amount=amount, from_wallet_id=wallet_id, to_wallet_id=t.id,
                     reason=reason, initiated_by_admin_id=admin_id, idempotency_key=key)
    s.add(tx); await s.flush()
    await ledger.post_legs(s, tx.id, [(wallet_id, asset.id, -amount), (t.id, asset.id, amount)])
    asset.total_supply = asset.total_supply - amount
    await s.flush()
    return tx
