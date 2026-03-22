from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# asyncpg does not reliably read sslmode from the URL — pass ssl=False explicitly
# for Fly.io internal (.flycast/.internal) connections that don't need TLS.
_url = settings.DATABASE_URL
_connect_args = {"ssl": False} if "flycast" in _url or "internal" in _url else {}

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
