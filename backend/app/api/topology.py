from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.device import Device
from app.models.topology import Building, Group, Site
from app.models.user import User
from app.schemas.topology import (
    BuildingCreate, BuildingResponse, BuildingUpdate,
    GroupCreate, GroupResponse, GroupUpdate,
    SiteCreate, SiteResponse, SiteUpdate,
)


class BulkDeleteRequest(BaseModel):
    ids: list[int]

router = APIRouter(tags=["topology"])


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupResponse])
async def list_groups(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Group).options(
            selectinload(Group.sites).selectinload(Site.buildings)
        )
    )
    groups = result.scalars().all()

    # Attach device counts to buildings
    device_counts = await db.execute(
        select(Device.building_id, func.count(Device.id)).group_by(Device.building_id)
    )
    count_map = {row[0]: row[1] for row in device_counts}

    response = []
    for g in groups:
        g_data = GroupResponse(id=g.id, name=g.name, description=g.description, sites=[])
        for s in g.sites:
            s_data = SiteResponse(id=s.id, group_id=s.group_id, name=s.name, description=s.description, buildings=[])
            for b in s.buildings:
                s_data.buildings.append(BuildingResponse(
                    id=b.id, site_id=b.site_id, name=b.name, floors=b.floors,
                    device_count=count_map.get(b.id, 0)
                ))
            g_data.sites.append(s_data)
        response.append(g_data)
    return response


@router.post("/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    group = Group(**body.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return GroupResponse(id=group.id, name=group.name, description=group.description, sites=[])


@router.patch("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    body: GroupUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(group, k, v)
    await db.commit()
    await db.refresh(group)
    return GroupResponse(id=group.id, name=group.name, description=group.description, sites=[])


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    await db.commit()


# ── Sites ─────────────────────────────────────────────────────────────────────

@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Group).where(Group.id == body.group_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Group not found")
    site = Site(**body.model_dump())
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return SiteResponse(id=site.id, group_id=site.group_id, name=site.name, description=site.description, buildings=[])


@router.patch("/sites/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    body: SiteUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(site, k, v)
    await db.commit()
    await db.refresh(site)
    return SiteResponse(id=site.id, group_id=site.group_id, name=site.name, description=site.description, buildings=[])


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    await db.delete(site)
    await db.commit()


# ── Buildings ─────────────────────────────────────────────────────────────────

@router.post("/buildings", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
async def create_building(
    body: BuildingCreate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Site).where(Site.id == body.site_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site not found")
    building = Building(**body.model_dump())
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return BuildingResponse(id=building.id, site_id=building.site_id, name=building.name, floors=building.floors)


@router.patch("/buildings/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: int,
    body: BuildingUpdate,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(building, k, v)
    await db.commit()
    await db.refresh(building)
    return BuildingResponse(id=building.id, site_id=building.site_id, name=building.name, floors=building.floors)


@router.delete("/buildings/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    await db.delete(building)
    await db.commit()


@router.get("/buildings/{building_id}/devices")
async def get_building_devices(
    building_id: int,
    floor: int | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    from app.schemas.device import DeviceResponse
    query = select(Device).where(Device.building_id == building_id)
    if floor is not None:
        query = query.where(Device.floor == floor)
    result = await db.execute(query)
    devices = result.scalars().all()
    return [DeviceResponse.model_validate(d) for d in devices]


@router.post("/groups/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_groups(
    body: BulkDeleteRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Group).where(Group.id.in_(body.ids)))
    for group in result.scalars().all():
        await db.delete(group)
    await db.commit()


@router.post("/sites/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_sites(
    body: BulkDeleteRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Site).where(Site.id.in_(body.ids)))
    for site in result.scalars().all():
        await db.delete(site)
    await db.commit()


@router.post("/buildings/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_delete_buildings(
    body: BulkDeleteRequest,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Building).where(Building.id.in_(body.ids)))
    for building in result.scalars().all():
        await db.delete(building)
    await db.commit()
