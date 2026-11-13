"""Swap between two virtual assets at the current DEMO prices. Atomic: burn(A) + mint(B) in one DB transaction;
both legs are balanced double-entry operations against the system treasury."""
from decimal import ROUND_DOWN, Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.models import Asset, Transaction, User, Wallet
from novaapi.services import ledger
from novaapi.services.settings import swap_cfg
from novaapi.services.swapmath import compute_quote
from novaapi.services.wallet import burn, mint


class SwapError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message


async def _pair(s: AsyncSession, sym_from: str, sym_to: str):
    rows = {a.symbol: a for a in (await s.execute(select(Asset).where(Asset.symbol.in_([sym_from.upper(), sym_to.upper()]), Asset.is_active))).scalars()}
    a, b = rows.get(sym_from.upper()), rows.get(sym_to.upper())
    if not a or not b or a.id == b.id:
        raise SwapError("invalid_pair", "Choose two different active assets")
    if a.virtual_price <= 0 or b.virtual_price <= 0:
        raise SwapError("no_price", "Price unavailable")
    return a, b


async def quote(s: AsyncSession, sym_from: str, sym_to: str, amount: Decimal) -> dict:
    a, b = await _pair(s, sym_from, sym_to)
    amount = amount.quantize(Decimal(1).scaleb(-a.decimal_precision), rounding=ROUND_DOWN)
    if amount <= 0:
        raise SwapError("invalid_amount", "Amount too small")
    c = await swap_cfg(s)
    q = compute_quote(a.virtual_price, b.virtual_price, amount, c["fee_percent"], b.decimal_precision)
    return {"from": a.symbol, "to": b.symbol, "amount_in": str(amount), "rate": str(q["rate"]), "fee": str(q["fee"]),
            "fee_percent": str(c["fee_percent"]), "amount_out": str(q["out"]), "demo": True}


async def execute(s: AsyncSession, user: User, sym_from: str, sym_to: str, amount: Decimal, min_receive: Decimal, key: str) -> dict:
    out_key, in_key = f"swap:{key}:out", f"swap:{key}:in"
    prev = (await s.execute(select(Transaction).where(Transaction.idempotency_key == in_key))).scalar_one_or_none()
    if prev:  # repeated request -> return the original result
        t_out = (await s.execute(select(Transaction).where(Transaction.idempotency_key == out_key))).scalar_one()
        return {"id": str(prev.id), "status": prev.status, "amount_in": str(t_out.amount), "amount_out": str(prev.amount), "fee": str(prev.fee)}
    if user.status != "active":
        raise SwapError("account_blocked", "Account restricted")
    w = (await s.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one()
    if w.status != "active":
        raise SwapError("wallet_frozen", "Wallet is frozen")
    a, b = await _pair(s, sym_from, sym_to)
    q = await quote(s, sym_from, sym_to, amount)
    amount_in, amount_out, fee = Decimal(q["amount_in"]), Decimal(q["amount_out"]), Decimal(q["fee"])
    if amount_out <= 0:
        raise SwapError("amount_too_small", "Amount too small for this pair")
    if amount_out < min_receive:
        raise SwapError("price_changed", "Price changed, please review the new quote")
    if b.max_supply is not None and b.total_supply + amount_out > b.max_supply:
        raise SwapError("supply_limit", "Target asset supply limit reached")
    try:
        await burn(s, w.id, a, amount_in, f"swap {a.symbol}->{b.symbol}", tx_type="swap_out", key=out_key)
        t_in = await mint(s, w.id, b, amount_out, "swap_in", f"swap {a.symbol}->{b.symbol}", key=in_key)
        t_in.fee = fee
        await s.commit()
    except ledger.InsufficientFunds:
        await s.rollback(); raise SwapError("insufficient_funds", "Insufficient balance")
    except IntegrityError:
        await s.rollback()
        prev = (await s.execute(select(Transaction).where(Transaction.idempotency_key == in_key))).scalar_one_or_none()
        if not prev:
            raise SwapError("supply_limit", "Operation violates supply limits")
        return {"id": str(prev.id), "status": prev.status, "amount_in": str(amount_in), "amount_out": str(prev.amount), "fee": str(prev.fee)}
    return {"id": str(t_in.id), "status": "completed", "amount_in": str(amount_in), "amount_out": str(amount_out), "fee": str(fee)}
