import uuid
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from novaapi.core.config import settings
from novaapi.core.db import SessionLocal
from novaapi.models import User
from novaapi.security.tokens import decode_token


async def get_session():
    async with SessionLocal() as s:
        yield s


async def current_user(authorization: str = Header(default=""), s: AsyncSession = Depends(get_session)) -> User:
    sub = decode_token(authorization.removeprefix("Bearer ").strip(), settings.secret_key)
    if not sub:
        raise HTTPException(401, "invalid or expired session")
    user = (await s.execute(select(User).where(User.id == uuid.UUID(sub)))).scalar_one_or_none()  # re-checked on every request
    if not user or user.is_system:
        raise HTTPException(401, "unknown user")
    return user


def internal_only(x_internal_key: str = Header(default="")):
    import hmac
    if not hmac.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(403, "forbidden")


async def refresh_prices(s: AsyncSession = Depends(get_session)) -> None:
    """DEMO market without a worker: generate missed price ticks lazily."""
    if settings.simulator_mode != "demo":
        return
    from novaapi.services import market_live
    try:
        await market_live.catch_up(s)
    except Exception:
        await s.rollback()
