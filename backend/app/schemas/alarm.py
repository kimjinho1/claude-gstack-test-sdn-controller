from datetime import datetime

from pydantic import BaseModel

from app.models.alarm import AlarmSeverity, AlarmStatus, AlarmType


class AlarmResponse(BaseModel):
    id: int
    device_id: int
    alarm_type: AlarmType
    severity: AlarmSeverity
    message: str
    status: AlarmStatus
    created_at: datetime
    resolved_at: datetime | None
    actions: list["AlarmActionResponse"] = []

    model_config = {"from_attributes": True}


class AlarmActionCreate(BaseModel):
    action_type: str
    note: str | None = None


class AlarmActionResponse(BaseModel):
    id: int
    alarm_id: int
    user_id: int
    action_type: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


AlarmResponse.model_rebuild()
