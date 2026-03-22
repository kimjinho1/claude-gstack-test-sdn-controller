from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import audit, get_current_user, require_admin
from app.core.database import get_db
from app.models.alarm import Alarm, AlarmAction, AlarmStatus
from app.models.user import User
from app.schemas.alarm import AlarmActionCreate, AlarmActionResponse, AlarmResponse

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.get("", response_model=list[AlarmResponse])
async def list_alarms(
    status: AlarmStatus | None = None,
    device_id: int | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    query = select(Alarm).options(selectinload(Alarm.actions)).order_by(Alarm.created_at.desc())
    if status:
        query = query.where(Alarm.status == status)
    if device_id:
        query = query.where(Alarm.device_id == device_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/{alarm_id}/acknowledge", response_model=AlarmResponse)
async def acknowledge_alarm(
    alarm_id: int,
    request: Request,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Alarm).options(selectinload(Alarm.actions)).where(Alarm.id == alarm_id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    if alarm.status != AlarmStatus.OPEN:
        raise HTTPException(status_code=409, detail=f"Alarm is already {alarm.status.value}")

    alarm.status = AlarmStatus.ACKNOWLEDGED
    await audit(db, user.id, "ALARM_ACK", resource_type="alarm", resource_id=alarm_id,
                ip_addr=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(alarm)
    return alarm


@router.post("/{alarm_id}/actions", response_model=AlarmActionResponse, status_code=201)
async def add_alarm_action(
    alarm_id: int,
    body: AlarmActionCreate,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Alarm).where(Alarm.id == alarm_id))
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")

    action = AlarmAction(
        alarm_id=alarm_id,
        user_id=user.id,
        action_type=body.action_type,
        note=body.note,
    )
    db.add(action)
    await db.flush()  # populate action.id without committing
    await audit(db, user.id, "ALARM_ACTION", resource_type="alarm", resource_id=alarm_id,
                ip_addr=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(action)
    return action
