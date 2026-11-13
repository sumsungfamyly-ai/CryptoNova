import os
from decimal import Decimal
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default="postgresql+asyncpg://cryptonova:change_me@localhost:5432/cryptonova",
                              validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"))
    redis_url: str = "redis://localhost:6379/0"
    bot_token: str = ""
    webhook_secret: str = ""
    cron_secret: str = ""
    mini_app_url: str = ""
    public_api_url: str = ""
    price_tick_seconds: int = 900
    secret_key: str = "change_me"
    internal_api_key: str = "change_me_internal"
    session_ttl_seconds: int = 3600
    cors_origins: str = "*"
    cookie_secure: bool = True
    admin_session_ttl_minutes: int = 60
    owner_bootstrap_email: str = ""
    owner_bootstrap_password: str = ""
    owner_totp_secret: str = ""
    initdata_max_age_seconds: int = 3600
    simulator_mode: str = "demo"
    transfer_fee_enabled: bool = False
    transfer_fee_percent: Decimal = Decimal("0")
    transfer_max_amount: Decimal = Decimal("1000000")
    daily_transfer_limit: Decimal = Decimal("1000000")  # virtual value per user per UTC day
    swap_fee_percent: Decimal = Decimal("0.5")
    starting_balances: str = "NUSD:1000,NBTC:0.05,NETH:0.5,NOVA:100,NGOLD:1"

    def parsed_starting_balances(self) -> dict[str, Decimal]:
        return {k: Decimal(v) for k, v in (p.split(":") for p in self.starting_balances.split(",") if p)}


settings = Settings()


def _derive(name: str) -> str:
    import hashlib, hmac
    return hmac.new((settings.database_url + settings.bot_token).encode(), name.encode(), hashlib.sha256).hexdigest()


# Unset secrets are derived from DATABASE_URL + BOT_TOKEN (unguessable without them) -> fewer variables to configure.
if settings.secret_key in ("", "change_me"):
    settings.secret_key = _derive("secret_key")
if settings.internal_api_key in ("", "change_me_internal"):
    settings.internal_api_key = _derive("internal_api_key")
if not settings.webhook_secret:
    settings.webhook_secret = _derive("webhook_secret")[:48]


def public_base(host: str | None = None) -> str:
    """Public https base URL of this deployment (Vercel production domain is auto-detected)."""
    if settings.public_api_url:
        return settings.public_api_url.rstrip("/")
    prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if prod:
        return f"https://{prod}"
    return f"https://{host}" if host else ""


def app_url() -> str:
    """Mini App and API share one domain, so MINI_APP_URL is optional."""
    return settings.mini_app_url.rstrip("/") or public_base()
