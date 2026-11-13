"""Turn any Postgres URL (Neon, Vercel, Render, local) into an asyncpg-compatible URL + connect args. Stdlib only."""
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SSL_ON = {"require", "verify-full", "verify-ca", "prefer", "true", "1"}


def normalize_db_url(url: str) -> tuple[str, dict]:
    u = urlsplit(url.strip())
    q = dict(parse_qsl(u.query))
    sslmode, ssl_q = q.pop("sslmode", None), q.pop("ssl", None)
    q.pop("channel_binding", None)
    q["prepared_statement_cache_size"] = "0"  # required behind pgbouncer / Neon pooler
    need_ssl = (sslmode or "").lower() in SSL_ON or (ssl_q or "").lower() in SSL_ON
    clean = urlunsplit(("postgresql+asyncpg", u.netloc, u.path, urlencode(q), ""))
    args = {"statement_cache_size": 0, "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__"}
    if need_ssl:
        args["ssl"] = True
    return clean, args
