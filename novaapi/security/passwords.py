"""Password hashing (scrypt) and TOTP (RFC 6238) — stdlib only."""
import base64, hashlib, hmac, os, struct, time

N, R, P = 2**14, 8, 1


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(h))
    except Exception:
        return False


def new_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode().rstrip("=")


def totp(secret: str, t: float | None = None, digits: int = 6, step: int = 30) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    h = hmac.new(key, struct.pack(">Q", int((time.time() if t is None else t) // step)), hashlib.sha1).digest()
    o = h[-1] & 15
    return str((struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 10**digits).zfill(digits)


def verify_totp(secret: str, code: str, now: float | None = None) -> bool:
    t = time.time() if now is None else now
    return any(hmac.compare_digest(totp(secret, t + d * 30), code.strip()) for d in (-1, 0, 1))
