from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alarms, auth, device_links, devices, topology, users
from app.core.config import settings
from app.core.database import engine
from app.core.security import hash_password
from app.models import alarm, device, topology as topo_models, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created by `alembic upgrade head` in the docker-compose entrypoint.
    # Only seed the initial user accounts here.
    await _seed_users()
    yield


async def _seed_users():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.database import AsyncSessionLocal
    from app.models.user import User, UserRole

    async with AsyncSessionLocal() as db:
        # Create jinhoadmin (SUPERADMIN) if not exists
        result = await db.execute(select(User).where(User.username == settings.SUPERADMIN_USERNAME))
        if not result.scalar_one_or_none():
            db.add(User(
                username=settings.SUPERADMIN_USERNAME,
                password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                role=UserRole.SUPERADMIN,
                must_change_password=False,
            ))

        # Create admin (ADMIN) if not exists
        result = await db.execute(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
        if not result.scalar_one_or_none():
            db.add(User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                must_change_password=True,  # Force password change on first login
            ))

        await db.commit()


app = FastAPI(
    title="SDN Controller",
    version="0.1.0",
    description="멀티벤더 네트워크 관리 플랫폼",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(topology.router)
app.include_router(devices.router)
app.include_router(device_links.router)
app.include_router(alarms.router)
app.include_router(users.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sdn-controller"}
