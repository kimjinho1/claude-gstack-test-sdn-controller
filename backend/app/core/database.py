from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# asyncpg does not support 'sslmode' as a URL parameter (libpq-only).
# Fly Postgres attach sets sslmode=require in the URL, which causes asyncpg
# to attempt TLS even on internal .flycast connections (which don't support TLS).
# Strip SSL params from the URL and pass ssl=False via connect_args instead.
_raw_url = settings.DATABASE_URL
_parsed = urlparse(_raw_url)
_qs = parse_qs(_parsed.query, keep_blank_values=True)
_qs.pop("sslmode", None)
_qs.pop("ssl", None)
_url = urlunparse(_parsed._replace(query=urlencode({k: v[0] for k, v in _qs.items()})))

_internal = "flycast" in _raw_url or ".internal" in _raw_url
_connect_args = {"ssl": False} if _internal else {}

engine = create_async_engine(_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
