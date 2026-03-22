"""Alarm generation task.

DEVICE_DOWN: triggered when consecutive_failures reaches 3 (health poll failures only).
DEVICE_UP:   triggered when a previously ERRORED device recovers to MANAGED.
INTERFACE_DOWN/UP: triggered by port status changes (Phase 2 — see TODOS.md).
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.tasks.celery_app import celery_app
from app.tasks.device_poll import _sync_db_session

logger = logging.getLogger(__name__)

DEVICE_DOWN_THRESHOLD = 3


@celery_app.task(name="app.tasks.alarm_check.check_all_devices")
def check_all_devices():
    from app.models.device import Device, DeviceStatus

    with _sync_db_session() as db:
        # Only load devices that may need alarm action:
        # - consecutive_failures >= threshold (candidate for DEVICE_DOWN)
        # - MANAGED with failures == 0 (candidate for DEVICE_UP / recovery)
        result = db.execute(
            select(Device).where(
                or_(
                    Device.consecutive_failures >= DEVICE_DOWN_THRESHOLD,
                    Device.status == DeviceStatus.MANAGED,
                )
            )
        )
        for device in result.scalars().all():
            try:
                _check_device_alarms(db, device)
            except Exception as exc:
                logger.error(f"Alarm check failed for device {device.id}: {exc}", exc_info=True)
                db.rollback()
        db.commit()


def _check_device_alarms(db, device):
    from app.models.alarm import Alarm, AlarmSeverity, AlarmStatus, AlarmType
    from app.models.device import DeviceStatus

    now = datetime.now(timezone.utc)

    # DEVICE_DOWN: consecutive_failures just reached threshold, no open DEVICE_DOWN alarm yet
    if device.consecutive_failures >= DEVICE_DOWN_THRESHOLD:
        existing = db.execute(
            select(Alarm).where(
                Alarm.device_id == device.id,
                Alarm.alarm_type == AlarmType.DEVICE_DOWN,
                Alarm.status == AlarmStatus.OPEN,
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(Alarm(
                device_id=device.id,
                alarm_type=AlarmType.DEVICE_DOWN,
                severity=AlarmSeverity.CRITICAL,
                message=f"Device {device.ip_addr} is unreachable ({device.consecutive_failures} consecutive failures)",
                status=AlarmStatus.OPEN,
            ))
            logger.warning(f"DEVICE_DOWN alarm for device {device.id}")

    # DEVICE_UP: device recovered (MANAGED + failures reset), auto-resolve DEVICE_DOWN
    if device.status == DeviceStatus.MANAGED and device.consecutive_failures == 0:
        open_down = db.execute(
            select(Alarm).where(
                Alarm.device_id == device.id,
                Alarm.alarm_type == AlarmType.DEVICE_DOWN,
                Alarm.status.in_([AlarmStatus.OPEN, AlarmStatus.ACKNOWLEDGED]),
            )
        ).scalars().all()
        for alarm in open_down:
            alarm.status = AlarmStatus.RESOLVED
            alarm.resolved_at = now
            # DEVICE_UP is an OPEN INFO alarm so operators see the recovery event
            db.add(Alarm(
                device_id=device.id,
                alarm_type=AlarmType.DEVICE_UP,
                severity=AlarmSeverity.INFO,
                message=f"Device {device.ip_addr} recovered",
                status=AlarmStatus.OPEN,
            ))
