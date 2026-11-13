import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from novaapi.api.v1 import admin, serverless
from novaapi.api.v1.routes import internal, router
from sqlalchemy import text
from novaapi.core.config import settings
from novaapi.core.db import SessionLocal
from novaapi.startup import ensure_ready

HINTS = {
    "OSError": "Не удаётся подключиться к базе: проверьте DATABASE_URL (подключена ли база в Storage?).",
    "ConnectionRefusedError": "Не удаётся подключиться к базе: проверьте DATABASE_URL.",
    "gaierror": "Адрес базы в DATABASE_URL не найден: проверьте строку.",
    "InvalidPasswordError": "Неверный пароль в DATABASE_URL.",
    "InvalidCatalogNameError": "Такой базы нет: проверьте имя базы в DATABASE_URL.",
    "TimeoutError": "База не ответила вовремя: обновите страницу через несколько секунд.",
    "CannotConnectNowError": "База просыпается: обновите страницу через несколько секунд.",
}
app = FastAPI(title="CryptoNOVA API", version="1.0.0", description="Educational simulator. All assets are virtual (DEMO).")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/v1/admin"):
        r.headers["Cache-Control"] = "no-store"
    return r


@app.middleware("http")
async def ready_guard(request: Request, call_next):
    if request.url.path != "/health":
        try:
            await ensure_ready(request.headers.get("x-forwarded-host") or request.headers.get("host"))
        except Exception:
            logging.exception("startup failed")
            return JSONResponse({"detail": "service not ready: check DATABASE_URL"}, status_code=503)
    return await call_next(request)


app.include_router(router)
app.include_router(admin.router)
app.include_router(internal)
app.include_router(serverless.public)
app.include_router(serverless.setup)


@app.get("/health")
async def health(request: Request):
    """Opening /health also triggers the one-time self-setup."""
    missing = [n for n, v in (("DATABASE_URL", os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")), ("BOT_TOKEN", settings.bot_token),
) if not v]
    err = hint = None
    owner = None
    try:
        await ensure_ready(request.headers.get("x-forwarded-host") or request.headers.get("host"))
        db = "ready"
        async with SessionLocal() as s:
            owner = (await s.execute(text("select count(*) from admins"))).scalar_one() > 0
        if not owner:
            hint = "Откройте /admin и создайте владельца (понадобится BOT_TOKEN)."
    except Exception as e:
        logging.exception("health")
        db, err = "unavailable", type(e).__name__
        hint = HINTS.get(err, "Откройте Vercel → Logs: там подробности. Проверьте DATABASE_URL и откройте /health ещё раз.")
    return {"status": "ok", "mode": settings.simulator_mode, "db": db, "error": err, "hint": hint, "missing_env": missing, "owner_created": owner}
