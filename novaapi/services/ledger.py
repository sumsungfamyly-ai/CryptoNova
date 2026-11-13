"""LedgerService: the ONLY code allowed to change balances.
Every call writes balanced ledger entries + updates balances in the caller's DB transaction."""
import uuid
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.models import Balance, LedgerEntry


class LedgerError(Exception):
    pass


class InsufficientFunds(LedgerError):
    pass


async def post_legs(s: AsyncSession, transaction_id: uuid.UUID, legs: list[tuple[uuid.UUID, uuid.UUID, Decimal]]) -> None:
    """legs = [(wallet_id, asset_id, signed_amount)]. Must sum to zero per asset."""
    totals: dict = defaultdict(Decimal)
    for _, asset_id, amt in legs:
        totals[asset_id] += amt
    if any(v != 0 for v in totals.values()):
        raise LedgerError("unbalanced legs")
    keys = sorted({(w, a) for w, a, _ in legs}, key=lambda k: (str(k[0]), str(k[1])))  # fixed lock order
    for w, a in keys:
        await s.execute(pg_insert(Balance).values(id=uuid.uuid4(), wallet_id=w, asset_id=a, amount=0)
                        .on_conflict_do_nothing(index_elements=["wallet_id", "asset_id"]))
    rows = {}
    for w, a in keys:
        rows[(w, a)] = (await s.execute(select(Balance).where(Balance.wallet_id == w, Balance.asset_id == a)
                                        .with_for_update())).scalar_one()
    for w, a, amt in legs:
        b = rows[(w, a)]
        new = b.amount + amt
        if new < 0 and not b.allow_negative:
            raise InsufficientFunds("insufficient balance")
        b.amount = new
        s.add(LedgerEntry(transaction_id=transaction_id, wallet_id=w, asset_id=a, amount=amt, balance_after=new))
    await s.flush()
