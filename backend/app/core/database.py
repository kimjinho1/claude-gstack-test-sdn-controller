from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Fly.io internal (.flycast/.internal) Postgres does not use TLS.
# asyncpg defaults to ssl=prefer which tries SSL first — but Fly internal Postgres
# accepts the SSLRequest with 'S', then resets the TLS handshake, causing
# ConnectionResetError. Passing ssl=False to asyncpg via connect_args skips
# SSL entirely. Note: connect_args={"ssl": False} works; sslmode=disable in
# the URL does NOT (asyncpg rejects unknown kwargs like 'sslmode').
_url = settings.DATABASE_URL
_internal = "flycast" in _url or ".internal" in _url
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
