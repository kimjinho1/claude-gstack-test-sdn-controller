from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alarms, auth, controller, device_links, devices, topology, users
from app.core.config import settings
from app.core.security import hash_password
from app.models import alarm, device, topology as topo_models, user
from app.models import controller as controller_models  # noqa: ensure tables are registered


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created by `alembic upgrade head` in the docker-compose entrypoint.
    # Only seed the initial user accounts here.
    await _seed_users()
    await _seed_device_models()
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


async def _seed_device_models():
    """Seed built-in device models if not already present."""
    from datetime import datetime, timezone
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.database import AsyncSessionLocal
    from app.models.controller import DeviceModel

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DeviceModel).where(DeviceModel.name == "cEOS-lab"))
        if not result.scalar_one_or_none():
            db.add(DeviceModel(
                name="cEOS-lab",
                vendor="Arista",
                device_type="arista_eos",
                description="Arista containerized EOS — lab/test virtual switch",
                docker_image="ceos:latest",
                is_virtual=True,
                created_at=datetime.now(timezone.utc),
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
app.include_router(controller.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sdn-controller"}
