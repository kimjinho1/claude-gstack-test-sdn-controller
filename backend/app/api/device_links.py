from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.device import Device, DeviceLink
from app.models.user import User

router = APIRouter(prefix="/device-links", tags=["device-links"])


class LinkCreate(BaseModel):
    parent_id: int
    child_id: int


class LinkResponse(BaseModel):
    id: int
    parent_id: int
    child_id: int

    model_config = {"from_attributes": True}


class DeviceNodeResponse(BaseModel):
    id: int
    name: str
    ip_addr: str
    status: str
    model: str | None
    protocol: str

    model_config = {"from_attributes": True}


class TopologyGraphResponse(BaseModel):
    devices: list[DeviceNodeResponse]
    links: list[LinkResponse]


@router.get("/graph", response_model=TopologyGraphResponse)
async def get_topology_graph(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return all devices and links in a single response for the topology view."""
    devices_result = await db.execute(select(Device))
    devices = devices_result.scalars().all()

    links_result = await db.execute(select(DeviceLink))
    links = links_result.scalars().all()

    return {"devices": devices, "links": links}


@router.get("", response_model=list[LinkResponse])
async def list_links(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceLink))
    return result.scalars().all()


@router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    body: LinkCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.parent_id == body.child_id:
        raise HTTPException(status_code=400, detail="상위/하위 장비가 같을 수 없습니다.")

    parent = await db.get(Device, body.parent_id)
    child = await db.get(Device, body.child_id)
    if not parent or not child:
        raise HTTPException(status_code=404, detail="장비를 찾을 수 없습니다.")

    existing = await db.execute(
        select(DeviceLink).where(
            DeviceLink.parent_id == body.parent_id,
            DeviceLink.child_id == body.child_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 링크입니다.")

    link = DeviceLink(parent_id=body.parent_id, child_id=body.child_id)
    db.add(link)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="이미 존재하는 링크입니다.")
    await db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    link = await db.get(DeviceLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="링크를 찾을 수 없습니다.")
    await db.delete(link)
    await db.commit()
