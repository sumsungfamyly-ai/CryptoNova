import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from novaapi.core.config import settings
from novaapi.core.dburl import normalize_db_url

DB_URL, CONNECT_ARGS = normalize_db_url(settings.database_url)
# Serverless (Vercel): no connection pool kept between invocations.
_pool = {"poolclass": NullPool} if os.getenv("VERCEL") else {"pool_pre_ping": True}
engine = create_async_engine(DB_URL, connect_args=CONNECT_ARGS, **_pool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
