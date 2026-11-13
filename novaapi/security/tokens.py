"""Minimal HS256 signed session tokens (stdlib only)."""
import base64, hashlib, hmac, json, time


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(sub: str, secret: str, ttl: int, now: float | None = None) -> str:
    h = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = _b64(json.dumps({"sub": sub, "exp": int((now or time.time()) + ttl)}).encode())
    sig = _b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def decode_token(token: str, secret: str, now: float | None = None) -> str | None:
    try:
        h, p, sig = token.split(".")
        good = _b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(good, sig):
            return None
        data = json.loads(_unb64(p))
        if data["exp"] < (now or time.time()):
            return None
        return data["sub"]
    except Exception:
        return None
