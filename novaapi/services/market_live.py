"""Serverless-friendly DEMO market: instead of a worker, missed ticks are generated lazily on request."""
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings
from novaapi.models import Asset, AssetPrice, Setting
from novaapi.services.pricesim import backfill, next_price

rng = random.Random()
MAX_CATCHUP = 96


async def set_anchor(s: AsyncSession, symbol: str, price: Decimal) -> None:
    key = f"anchor:{symbol}"
    row = (await s.execute(select(Setting).where(Setting.key == key))).scalar_one_or_none()
    if row:
        row.value = {"p": str(price)}
    else:
        s.add(Setting(key=key, value={"p": str(price)}))


async def _anchors(s: AsyncSession) -> dict:
    return {r.key[7:]: Decimal(r.value["p"]) for r in (await s.execute(select(Setting).where(Setting.key.like("anchor:%")))).scalars()}


async def catch_up(s: AsyncSession) -> int:
    tick = timedelta(seconds=settings.price_tick_seconds)
    now = datetime.now(timezone.utc)
    last = (await s.execute(select(func.max(AssetPrice.created_at)))).scalar_one_or_none()
    if last and now - last < tick:
        return 0
    if not (await s.execute(text("select pg_try_advisory_xact_lock(727001)"))).scalar_one():
        return 0  # another request is already generating ticks
    last = (await s.execute(select(func.max(AssetPrice.created_at)))).scalar_one_or_none()
    if last and now - last < tick:
        await s.rollback(); return 0
    n = 1 if not last else max(1, min(MAX_CATCHUP, int((now - last) / tick)))
    anchors = await _anchors(s)
    for a in (await s.execute(select(Asset).where(Asset.is_demo, Asset.is_active, Asset.virtual_price > 0))).scalars():
        if a.symbol not in anchors:
            anchors[a.symbol] = a.virtual_price; await set_anchor(s, a.symbol, a.virtual_price)
        p = a.virtual_price
        for i in range(n):
            p = next_price(p, anchors[a.symbol], a.category, rng)
            ts = now - tick * (n - 1 - i)
            s.add(AssetPrice(asset_id=a.id, price=p, created_at=ts, updated_at=ts))
        a.virtual_price = p
    await s.commit()
    return n


async def backfill_session(s: AsyncSession, days: int) -> int:
    now, added = datetime.now(timezone.utc), 0
    for a in (await s.execute(select(Asset).where(Asset.is_demo))).scalars():
        cnt = (await s.execute(select(func.count()).select_from(AssetPrice).where(AssetPrice.asset_id == a.id))).scalar_one()
        if cnt > 1 or a.virtual_price <= 0:
            continue
        for t, p in backfill(a.virtual_price, a.category, days * 24, timedelta(hours=1), now, rng):
            s.add(AssetPrice(asset_id=a.id, price=p, created_at=t, updated_at=t)); added += 1
    await s.commit()
    return added
