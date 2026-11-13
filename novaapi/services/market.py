from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.models import Asset, AssetPrice, Balance, Wallet

RANGES = {"1H": timedelta(hours=1), "24H": timedelta(hours=24), "7D": timedelta(days=7),
          "30D": timedelta(days=30), "90D": timedelta(days=90), "ALL": None}


async def record_price(s: AsyncSession, asset: Asset) -> None:
    s.add(AssetPrice(asset_id=asset.id, price=asset.virtual_price))
    await s.flush()


async def history(s: AsyncSession, asset: Asset, rng: str) -> list[dict]:
    delta = RANGES.get(rng.upper(), RANGES["24H"])
    now = datetime.now(timezone.utc)
    st = select(AssetPrice).where(AssetPrice.asset_id == asset.id).order_by(AssetPrice.created_at)
    if delta:
        st = st.where(AssetPrice.created_at >= now - delta)
    pts = [{"t": p.created_at.isoformat(), "p": str(p.price)} for p in (await s.execute(st)).scalars()]
    if delta:  # carry the last known price from before the window so the line has a start
        prev = (await s.execute(select(AssetPrice).where(AssetPrice.asset_id == asset.id, AssetPrice.created_at < now - delta)
                                .order_by(AssetPrice.created_at.desc()).limit(1))).scalar_one_or_none()
        if prev:
            pts.insert(0, {"t": (now - delta).isoformat(), "p": str(prev.price)})
    pts.append({"t": now.isoformat(), "p": str(asset.virtual_price)})
    return pts


async def change_pct(s: AsyncSession, asset: Asset, hours: int = 24) -> str | None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    ref = (await s.execute(select(AssetPrice).where(AssetPrice.asset_id == asset.id, AssetPrice.created_at <= cutoff)
                           .order_by(AssetPrice.created_at.desc()).limit(1))).scalar_one_or_none()
    if not ref:
        ref = (await s.execute(select(AssetPrice).where(AssetPrice.asset_id == asset.id)
                               .order_by(AssetPrice.created_at).limit(1))).scalar_one_or_none()
    if not ref or ref.price == 0:
        return None
    return str(((asset.virtual_price - ref.price) / ref.price * 100).quantize(Decimal("0.01")))


async def portfolio_history(s: AsyncSession, user_id, rng: str) -> list[dict]:
    """Current holdings valued at recorded historical prices (not a reconstruction of past holdings)."""
    w = (await s.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one()
    rows = (await s.execute(select(Balance, Asset).join(Asset, Asset.id == Balance.asset_id)
                            .where(Balance.wallet_id == w.id, Balance.amount > 0))).all()
    series = {a.symbol: (b.amount, await history(s, a, rng)) for b, a in rows}
    times = sorted({p["t"] for _, pts in series.values() for p in pts})
    out = []
    for t in times:
        total = Decimal(0)
        for amount, pts in series.values():
            price = next((Decimal(p["p"]) for p in reversed(pts) if p["t"] <= t), Decimal(pts[0]["p"]))
            total += amount * price
        out.append({"t": t, "v": str(total)})
    return out
