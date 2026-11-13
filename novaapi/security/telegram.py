"""Telegram Mini App initData validation (HMAC-SHA256), per Telegram docs."""
import hashlib, hmac, json, time
from urllib.parse import parse_qsl


class InitDataError(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str, max_age: int = 3600, now: float | None = None) -> dict:
    if not init_data or not bot_token:
        raise InitDataError("missing data")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    received = pairs.pop("hash", None)
    if not received:
        raise InitDataError("missing hash")
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InitDataError("bad signature")
    try:
        auth_date = int(pairs["auth_date"])
    except (KeyError, ValueError):
        raise InitDataError("bad auth_date")
    t = time.time() if now is None else now
    if t - auth_date > max_age or auth_date - t > 60:
        raise InitDataError("expired")
    try:
        user = json.loads(pairs["user"])
        int(user["id"])
    except Exception:
        raise InitDataError("bad user")
    return user
