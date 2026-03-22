import asyncio
import re
import subprocess
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.controller import DeviceModel, VirtualDevice
from app.models.user import User
from app.schemas.controller import (
    DeviceModelCreate,
    DeviceModelResponse,
    DeviceModelUpdate,
    VirtualDeviceLaunch,
    VirtualDeviceResponse,
)

router = APIRouter(prefix="/controller", tags=["controller"])

# Docker container ID is a 64-char hex string
_CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
# Allowed characters in container name (Docker rules)
_SAFE_NAME_RE = re.compile(r"[^a-z0-9_-]")


# ── Device Models ──────────────────────────────────────────────────────────────

@router.get("/device-models", response_model=list[DeviceModelResponse])
async def list_device_models(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceModel).order_by(DeviceModel.id))
    return result.scalars().all()


@router.post("/device-models", response_model=DeviceModelResponse, status_code=201)
async def create_device_model(
    body: DeviceModelCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    model = DeviceModel(**body.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.patch("/device-models/{model_id}", response_model=DeviceModelResponse)
async def update_device_model(
    model_id: int,
    body: DeviceModelUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceModel).where(DeviceModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Device model not found")
    for key, val in body.model_dump(exclude_none=True).items():
        setattr(model, key, val)
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/device-models/{model_id}", status_code=204)
async def delete_device_model(
    model_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceModel).where(DeviceModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Device model not found")
    await db.delete(model)
    await db.commit()


# ── Virtual Devices ────────────────────────────────────────────────────────────

@router.get("/virtual-devices", response_model=list[VirtualDeviceResponse])
async def list_virtual_devices(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(VirtualDevice).order_by(VirtualDevice.id))
    devices = result.scalars().all()
    # Sync status from Docker for running containers (offloaded to thread pool)
    for vd in devices:
        if vd.container_id and vd.status in ("running", "starting"):
            vd.status = await asyncio.to_thread(_docker_container_status, vd.container_id)
    if db.dirty:
        await db.commit()
    return devices


@router.post("/virtual-devices", response_model=VirtualDeviceResponse, status_code=201)
async def launch_virtual_device(
    body: VirtualDeviceLaunch,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Validate model exists and has a docker_image
    result = await db.execute(select(DeviceModel).where(DeviceModel.id == body.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Device model not found")
    if not model.docker_image:
        raise HTTPException(status_code=400, detail="This device model has no docker_image configured")

    # Check port not already in use by another virtual device
    port_result = await db.execute(
        select(VirtualDevice).where(
            VirtualDevice.ssh_port == body.ssh_port,
            VirtualDevice.status != "stopped",
        )
    )
    if port_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"SSH port {body.ssh_port} is already in use by another virtual device")

    vd = VirtualDevice(
        name=body.name,
        model_id=body.model_id,
        ssh_port=body.ssh_port,
        status="starting",
    )
    db.add(vd)
    await db.commit()
    await db.refresh(vd)

    # Sanitize name for Docker container naming (alphanumeric, hyphens, underscores only)
    safe_name = _SAFE_NAME_RE.sub("-", body.name.lower())
    container_name = f"vdev-{vd.id}-{safe_name}"

    # Launch container off the async event loop to avoid blocking
    docker_image = model.docker_image
    ssh_port = body.ssh_port

    def _launch():
        return subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{ssh_port}:22",
                "-e", "INTFTYPE=eth",
                "-e", "ETBA=1",
                "-e", "SKIP_ZEROTOUCH_BARRIER_IN_SYSDBINIT=1",
                "-e", "CEOS=1",
                "-e", "EOS_PLATFORM=ceoslab",
                docker_image,
                "/sbin/init",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    try:
        proc = await asyncio.to_thread(_launch)
        if proc.returncode == 0:
            container_id = proc.stdout.strip()
            # Validate Docker returns a proper 64-char hex container ID
            if _CONTAINER_ID_RE.match(container_id):
                vd.container_id = container_id
                vd.status = "running"
            else:
                vd.status = "error"
        else:
            vd.status = "error"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        vd.status = "error"

    await db.commit()
    await db.refresh(vd)
    return vd


@router.post("/virtual-devices/{vd_id}/stop", response_model=VirtualDeviceResponse)
async def stop_virtual_device(
    vd_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(VirtualDevice).where(VirtualDevice.id == vd_id))
    vd = result.scalar_one_or_none()
    if not vd:
        raise HTTPException(status_code=404, detail="Virtual device not found")

    if vd.container_id:
        container_id = vd.container_id
        await asyncio.to_thread(
            lambda: subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True, timeout=15,
            )
        )

    vd.status = "stopped"
    vd.stopped_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(vd)
    return vd


@router.delete("/virtual-devices/{vd_id}", status_code=204)
async def delete_virtual_device(
    vd_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(VirtualDevice).where(VirtualDevice.id == vd_id))
    vd = result.scalar_one_or_none()
    if not vd:
        raise HTTPException(status_code=404, detail="Virtual device not found")

    # Force-remove container if still running (off event loop)
    if vd.container_id:
        container_id = vd.container_id
        await asyncio.to_thread(
            lambda: subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True, timeout=15,
            )
        )

    await db.delete(vd)
    await db.commit()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _docker_container_status(container_id: str) -> str:
    """Return 'running' | 'stopped' | 'error' for a Docker container.
    Runs synchronously — must be called via asyncio.to_thread()."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_id],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            state = result.stdout.strip()
            return "running" if state == "running" else "stopped"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return "error"
