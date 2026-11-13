import hmac, logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from novaapi import seed, telegram_bot
from novaapi.api.deps import internal_only
from novaapi.bootstrap_owner import create_owner
from novaapi.core.config import public_base, settings
from novaapi.core.db import SessionLocal
from novaapi.db_init import init_db
from novaapi.services import market_live, notifier

public = APIRouter()
setup = APIRouter(prefix="/internal", dependencies=[Depends(internal_only)])


@public.post("/api/v1/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str = Header(default="")):
    if not settings.webhook_secret or not hmac.compare_digest(x_telegram_bot_api_secret_token, settings.webhook_secret):
        raise HTTPException(403, "forbidden")
    try:
        await telegram_bot.process_update(await request.json())
    except Exception:
        logging.exception("webhook")
    return {"ok": True}  # always 200 so Telegram does not retry-storm


@public.get("/internal/cron")
async def cron(authorization: str = Header(default="")):
    if not settings.cron_secret or not hmac.compare_digest(authorization, f"Bearer {settings.cron_secret}"):
        raise HTTPException(403, "forbidden")
    out = {"ticks": 0, "sent": 0}
    async with SessionLocal() as s:
        if settings.simulator_mode == "demo":
            out["ticks"] = await market_live.catch_up(s)
        for _ in range(6):
            r = await notifier.deliver(s, limit=25); out["sent"] += r["sent"]
            if not r["remaining"] or not r["sent"]:
                break
    return out


@setup.post("/bootstrap")
async def bootstrap(backfill_days: int = 30):
    """One-time (idempotent) setup: schema + triggers + seed + OWNER + chart history."""
    await init_db()
    await seed.main()
    owner = await create_owner()
    added = 0
    async with SessionLocal() as s:
        if settings.simulator_mode == "demo" and backfill_days > 0:
            added = await market_live.backfill_session(s, min(backfill_days, 365))
    return {"schema": "ok", "seed": "ok", "owner": owner, "price_points_added": added}


@setup.post("/setup-webhook")
async def setup_webhook(request: Request):
    if not settings.bot_token or not settings.webhook_secret:
        raise HTTPException(400, "set BOT_TOKEN and WEBHOOK_SECRET first")
    base = public_base(request.headers.get("x-forwarded-host") or request.headers.get("host"))
    return await telegram_bot.setup_webhook(base)
