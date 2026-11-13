import uuid
from decimal import ROUND_DOWN, Decimal
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings
from novaapi.models import Asset, Transaction, User, Wallet
from novaapi.services import ledger, notifier, notify
from novaapi.services.settings import transfer_cfg
from novaapi.services.wallet import treasury_wallet


class TransferError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message


async def find_user(s: AsyncSession, q: str) -> User | None:
    q = q.strip().lstrip("@")
    if not q:
        return None
    stmt = select(User).where(User.is_system.is_(False))
    try:
        stmt = stmt.where(User.id == uuid.UUID(q))
    except ValueError:
        if q.upper().startswith("NW-"):
            stmt = stmt.join(Wallet, Wallet.user_id == User.id).where(Wallet.public_id == q.upper())
        else:
            stmt = stmt.where(func.lower(User.username) == q.lower())
    return (await s.execute(stmt)).scalars().first()


async def send(s: AsyncSession, sender: User, recipient_q: str, symbol: str, amount: Decimal, key: str) -> Transaction:
    if not key:
        raise TransferError("idempotency_required", "Idempotency key required")
    existing = (await s.execute(select(Transaction).where(Transaction.idempotency_key == key))).scalar_one_or_none()
    if existing:
        return existing
    if sender.status != "active":
        raise TransferError("account_blocked", "Account restricted")
    rec = await find_user(s, recipient_q)
    if not rec:
        raise TransferError("recipient_not_found", "Recipient not found")
    if rec.id == sender.id:
        raise TransferError("self_transfer", "Cannot send to yourself")
    if rec.status != "active":
        raise TransferError("recipient_blocked", "Recipient unavailable")
    sw = (await s.execute(select(Wallet).where(Wallet.user_id == sender.id))).scalar_one()
    rw = (await s.execute(select(Wallet).where(Wallet.user_id == rec.id))).scalar_one()
    if sw.status != "active" or rw.status != "active":
        raise TransferError("wallet_frozen", "Wallet is frozen")
    asset = (await s.execute(select(Asset).where(Asset.symbol == symbol.upper(), Asset.is_active))).scalar_one_or_none()
    if not asset:
        raise TransferError("asset_not_found", "Asset not available")
    amount = amount.quantize(Decimal(1).scaleb(-asset.decimal_precision), rounding=ROUND_DOWN)
    if amount <= 0:
        raise TransferError("invalid_amount", "Amount must be positive")
    cfg = await transfer_cfg(s)
    if amount > cfg['max_amount']:
        raise TransferError("limit_exceeded", "Maximum transfer amount exceeded")
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    spent = (await s.execute(select(func.coalesce(func.sum(Transaction.amount * Asset.virtual_price), 0)).join(Asset, Asset.id == Transaction.asset_id)
                             .where(Transaction.type == "transfer", Transaction.from_wallet_id == sw.id, Transaction.created_at >= midnight))).scalar_one()
    if Decimal(spent) + amount * asset.virtual_price > cfg["daily_limit"]:
        raise TransferError("daily_limit", "Daily transfer limit exceeded")
    fee = Decimal(0)
    if cfg['fee_enabled'] and cfg['fee_percent'] > 0:
        fee = (amount * cfg['fee_percent'] / 100).quantize(Decimal(1).scaleb(-asset.decimal_precision), rounding=ROUND_DOWN)
    tx = Transaction(type="transfer", asset_id=asset.id, amount=amount, fee=fee, from_wallet_id=sw.id,
                     to_wallet_id=rw.id, idempotency_key=key)
    s.add(tx)
    try:
        await s.flush()
    except IntegrityError:  # concurrent duplicate request
        await s.rollback()
        return (await s.execute(select(Transaction).where(Transaction.idempotency_key == key))).scalar_one()
    legs = [(sw.id, asset.id, -(amount + fee)), (rw.id, asset.id, amount)]
    if fee > 0:
        legs.append(((await treasury_wallet(s)).id, asset.id, fee))
    try:
        await ledger.post_legs(s, tx.id, legs)
    except ledger.InsufficientFunds:
        await s.rollback()
        raise TransferError("insufficient_funds", "Insufficient balance")
    base = {"tx_id": str(tx.id), "symbol": asset.symbol, "amount": str(amount)}
    await notify.enqueue(s, sender.id, "transfer_sent", {**base, "to": rec.username or str(rec.id)}, f"transfer_sent:{tx.id}")
    await notify.enqueue(s, rec.id, "transfer_received", {**base, "from": sender.username or str(sender.id)}, f"transfer_received:{tx.id}")
    await s.commit()
    try:
        await notifier.deliver(s, limit=10, user_ids=[sender.id, rec.id])
    except Exception:
        pass  # delivery must never fail a completed transfer
    return tx
