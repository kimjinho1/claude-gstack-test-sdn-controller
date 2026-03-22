from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AlarmType(str, PyEnum):
    DEVICE_DOWN = "DEVICE_DOWN"
    DEVICE_UP = "DEVICE_UP"
    INTERFACE_DOWN = "INTERFACE_DOWN"
    INTERFACE_UP = "INTERFACE_UP"
    POLL_TIMEOUT = "POLL_TIMEOUT"


class AlarmSeverity(str, PyEnum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class AlarmStatus(str, PyEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    alarm_type: Mapped[AlarmType] = mapped_column(Enum(AlarmType), nullable=False)
    severity: Mapped[AlarmSeverity] = mapped_column(Enum(AlarmSeverity), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AlarmStatus] = mapped_column(
        Enum(AlarmStatus), nullable=False, default=AlarmStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped["Device"] = relationship("Device", back_populates="alarms")
    actions: Mapped[list["AlarmAction"]] = relationship("AlarmAction", back_populates="alarm", cascade="all, delete-orphan")


class AlarmAction(Base):
    __tablename__ = "alarm_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    alarm_id: Mapped[int] = mapped_column(ForeignKey("alarms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    alarm: Mapped["Alarm"] = relationship("Alarm", back_populates="actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[int | None] = mapped_column(Integer)
    ip_addr: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
