from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Fly.io internal (.flycast/.internal) Postgres does NOT use TLS.
# asyncpg parses sslmode from the DSN, so strip any existing sslmode and
# add sslmode=disable for internal connections. Note: connect_args={"ssl": False}
# does NOT work because SQLAlchemy's asyncpg dialect drops it silently (if ssl:).
_raw_url = settings.DATABASE_URL
_parsed = urlparse(_raw_url)
_qs = parse_qs(_parsed.query, keep_blank_values=True)
_qs.pop("sslmode", None)
_qs.pop("ssl", None)

_internal = "flycast" in _raw_url or ".internal" in _raw_url
if _internal:
    _qs["sslmode"] = ["disable"]

_url = urlunparse(_parsed._replace(query=urlencode({k: v[0] for k, v in _qs.items()})))

engine = create_async_engine(_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
