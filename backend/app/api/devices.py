import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import audit, get_current_user, require_admin
from app.protocols.ssh.ssh_driver import get_ssh_driver
from app.tasks.device_poll import poll_device_task
from app.core.database import get_db
from app.core.security import decrypt_credential, encrypt_credential
from app.models.device import Device, DevicePort, DeviceProtocol, DeviceStatus, Endpoint, Vlan
from app.models.user import User
from app.schemas.device import (
    DeviceCreate, DeviceResponse, DeviceUpdate,
    EndpointResponse, PortResponse, VlanResponse,
)

router = APIRouter(prefix="/devices", tags=["devices"])


class BulkDeleteRequest(BaseModel):
    ids: list[int]


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    site_id: int | None = None,
    building_id: int | None = None,
    status: DeviceStatus | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    query = select(Device)
    if site_id:
        query = query.where(Device.site_id == site_id)
    if building_id:
        query = query.where(Device.building_id == building_id)
    if status:
        query = query.where(Device.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    body: DeviceCreate,
    request: Request,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.protocol == DeviceProtocol.REST:
        # REST is Phase 2 — accept registration but mark as unsupported for now
        pass

    device = Device(
        name=body.name,
        mac_addr=body.mac_addr,
        ip_addr=body.ip_addr,
        site_id=body.site_id,
        building_id=body.building_id,
        floor=body.floor,
        protocol=body.protocol,
        device_type=body.device_type,
        model_id=body.model_id,
        status=DeviceStatus.PENDING,
    )

    if body.protocol == DeviceProtocol.SSH:
        device.ssh_id = body.ssh_id
        device.ssh_password_encrypted = encrypt_credential(body.ssh_password)
        device.ssh_port = body.ssh_port or 22
    else:
        device.rest_id = body.rest_id
        device.rest_password_encrypted = encrypt_credential(body.rest_password)
        device.rest_port = body.rest_port

    db.add(device)
    await db.flush()  # populate device.id without committing
    await audit(db, user.id, "DEVICE_ADD", resource_type="device", resource_id=device.id,
                ip_addr=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(device)

    # Trigger immediate polling
    poll_device_task.delay(device.id)

    return device


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "ssh_password":
            device.ssh_password_encrypted = encrypt_credential(v)
        elif k == "rest_password":
            device.rest_password_encrypted = encrypt_credential(v)
        else:
            setattr(device, k, v)

    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()


@router.post("/bulk-delete", status_code=204)
async def bulk_delete_devices(
    body: BulkDeleteRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id.in_(body.ids)))
    for device in result.scalars().all():
        await db.delete(device)
    await db.commit()


def _require_managed(device: Device):
    if device.status != DeviceStatus.MANAGED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device is {device.status.value}, not MANAGED. Queries require MANAGED status."
        )


@router.get("/{device_id}/ports", response_model=list[PortResponse])
async def get_ports(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    _require_managed(device)

    ports = await db.execute(select(DevicePort).where(DevicePort.device_id == device_id))
    return ports.scalars().all()


@router.get("/{device_id}/vlans", response_model=list[VlanResponse])
async def get_vlans(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    _require_managed(device)

    vlans = await db.execute(select(Vlan).where(Vlan.device_id == device_id))
    return vlans.scalars().all()


@router.post("/{device_id}/running-config")
async def fetch_running_config(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    _require_managed(device)
    if device.protocol != DeviceProtocol.SSH:
        raise HTTPException(status_code=400, detail="Running config은 SSH 장비만 지원합니다")

    ip = device.ip_addr
    ssh_id = device.ssh_id
    password = decrypt_credential(device.ssh_password_encrypted)
    port = device.ssh_port or 22
    device_type = device.device_type or "cisco_ios"

    def _fetch():
        driver = get_ssh_driver(ip=ip, username=ssh_id, password=password, port=port, device_type=device_type)
        try:
            return driver.get_running_config()
        finally:
            driver.close()

    try:
        config = await asyncio.to_thread(_fetch)
    except RuntimeError as e:
        msg = str(e)
        # "not supported" → 501, device rejected command → 422, else → 502
        if "지원되지 않습니다" in msg:
            raise HTTPException(status_code=501, detail=msg)
        if "명령어를 거부" in msg:
            raise HTTPException(status_code=422, detail=msg)
        raise HTTPException(status_code=502, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SSH 연결 실패: {e}")
    return {"config": config}


@router.post("/{device_id}/poll")
async def trigger_poll(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    _require_managed(device)
    poll_device_task.delay(device_id)
    return {"queued": True}


@router.get("/{device_id}/endpoints", response_model=list[EndpointResponse])
async def get_endpoints(
    device_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    _require_managed(device)

    endpoints = await db.execute(select(Endpoint).where(Endpoint.device_id == device_id))
    return endpoints.scalars().all()
