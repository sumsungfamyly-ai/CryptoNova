from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings as env
from novaapi.models import Setting


async def transfer_cfg(s: AsyncSession) -> dict:
    rows = {r.key: r.value for r in (await s.execute(select(Setting))).scalars()}
    fee = rows.get("transfer_fee", {})
    return {"fee_enabled": bool(fee.get("enabled", env.transfer_fee_enabled)),
            "fee_percent": Decimal(str(fee.get("percent", env.transfer_fee_percent))),
            "max_amount": Decimal(str(rows.get("transfer_max_amount", {}).get("value", env.transfer_max_amount))),
            "daily_limit": Decimal(str(rows.get("daily_limit", {}).get("value", env.daily_transfer_limit)))}


async def swap_cfg(s: AsyncSession) -> dict:
    row = (await s.execute(select(Setting).where(Setting.key == "swap_fee"))).scalar_one_or_none()
    return {"fee_percent": Decimal(str((row.value if row else {}).get("percent", env.swap_fee_percent)))}
