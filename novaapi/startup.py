"""First-start self-setup: creates schema/triggers, seed, OWNER, chart history and the Telegram webhook automatically.
Runs once per instance (cheap check), guarded by a transaction-level advisory lock (safe with Neon's pooler)."""
import logging
from novaapi import seed, telegram_bot
from novaapi.bootstrap_owner import create_owner
from novaapi.core.config import public_base, settings
from novaapi.core.db import SessionLocal, engine
from novaapi.db_init import init_db
from novaapi.services import market_live

SCHEMA_VERSION = "3"  # bump when models/constraints change: triggers an idempotent upgrade on the next start
_ready = False


async def ensure_ready(host: str | None = None) -> None:
    global _ready
    if _ready:
        return
    async with engine.begin() as lock:
        await lock.exec_driver_sql("select pg_advisory_xact_lock(727002)")
        fresh = (await lock.exec_driver_sql("select to_regclass('public.assets')::text")).scalar() is None
        ver = None if fresh else (await lock.exec_driver_sql("select value->>'v' from settings where key='schema_version'")).scalar()
        first_run = fresh or ver != SCHEMA_VERSION
        if first_run:
            await init_db()   # idempotent: new tables, triggers, constraints
            await seed.main()  # idempotent: only adds what is missing (e.g. new settings)
            await lock.exec_driver_sql(f"insert into settings (id, key, value) values (gen_random_uuid(), 'schema_version', '{{\"v\": \"{SCHEMA_VERSION}\"}}'::jsonb) "
                                       "on conflict (key) do update set value = excluded.value")
        if (await lock.exec_driver_sql("select count(*) from admins")).scalar() == 0:
            logging.info("owner bootstrap: %s", (await create_owner()).get("status"))
        if first_run:
            if settings.simulator_mode == "demo":
                async with SessionLocal() as s:
                    await market_live.backfill_session(s, 30)
            if settings.bot_token and settings.webhook_secret and public_base(host):
                try:
                    logging.info("webhook: %s", await telegram_bot.setup_webhook(public_base(host)))
                except Exception:
                    logging.exception("webhook setup failed (retry: POST /internal/setup-webhook)")
    _ready = True
