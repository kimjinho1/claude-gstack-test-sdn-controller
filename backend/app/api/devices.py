from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import audit, get_current_user, require_admin
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

    for k, v in body.model_dump(exclude_none=True).items():
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
