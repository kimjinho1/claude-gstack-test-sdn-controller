"""Test fixtures for SDN Controller backend."""
import os

# Set test secrets BEFORE importing app modules — Settings() is instantiated at module load.
os.environ.setdefault("MASTER_SECRET", "test_secret_32chars_for_pytest_only")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_for_pytest_only_xxxxx")
os.environ.setdefault("SUPERADMIN_PASSWORD", "test_superadmin_password_for_pytest")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    AsyncSessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    """AsyncClient with in-memory SQLite DB injected."""
    AsyncSessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Seed default users
    async with AsyncSessionLocal() as session:
        session.add(User(
            username="jinhoadmin",
            password_hash=hash_password("superpass"),
            role=UserRole.SUPERADMIN,
            must_change_password=False,
        ))
        session.add(User(
            username="admin",
            password_hash=hash_password("admin"),
            role=UserRole.ADMIN,
            must_change_password=True,
        ))
        session.add(User(
            username="viewer",
            password_hash=hash_password("viewer"),
            role=UserRole.VIEWER,
            must_change_password=False,
        ))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client):
    """Return a valid JWT for the admin user (after password change)."""
    # admin must change password first — use jinhoadmin instead
    resp = await client.post("/auth/login", json={"username": "jinhoadmin", "password": "superpass"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def viewer_token(client):
    resp = await client.post("/auth/login", json={"username": "viewer", "password": "viewer"})
    assert resp.status_code == 200
    return resp.json()["access_token"]
