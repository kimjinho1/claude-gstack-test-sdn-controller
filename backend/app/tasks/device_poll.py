"""Device polling tasks.

Polling strategy:
  PENDING/ERROR  → collect system info (uptime/serial/model/sw_version) → MANAGED if all fields present
  MANAGED        → refresh system info + ports + vlans + endpoints
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.security import decrypt_credential
from app.protocols.ssh.ssh_driver import get_ssh_driver
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_PENDING_RETRIES = 10

# Module-level engine singleton — created once per worker process, not per task call.
# Prevents PostgreSQL connection exhaustion when polling 100+ devices per minute.
_sync_engine = None
_SyncSession = None


def _get_sync_session():
    """Return a synchronous DB session for use inside Celery tasks."""
    global _sync_engine, _SyncSession
    if _sync_engine is None:
        from app.core.config import settings
        sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        _sync_engine = create_engine(sync_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        _SyncSession = sessionmaker(_sync_engine)
    return _SyncSession()


# Keep old name as alias so alarm_check.py import continues to work
_sync_db_session = _get_sync_session


@celery_app.task(name="app.tasks.device_poll.poll_device_task", bind=True, max_retries=3)
def poll_device_task(self, device_id: int):
    """Immediately poll a single device (triggered on registration)."""
    from sqlalchemy import select

    from app.models.device import Device

    with _get_sync_session() as db:
        device = db.execute(select(Device).where(Device.id == device_id)).scalar_one_or_none()
        if not device:
            return

        _poll_device(db, device)


@celery_app.task(name="app.tasks.device_poll.poll_pending_devices")
def poll_pending_devices():
    """Poll all PENDING and ERROR devices to attempt MANAGED transition."""
    from sqlalchemy import select

    from app.models.device import Device, DeviceStatus

    with _get_sync_session() as db:
        result = db.execute(
            select(Device).where(Device.status.in_([DeviceStatus.PENDING, DeviceStatus.ERROR]))
        )
        devices = result.scalars().all()
        for device in devices:
            poll_device_task.delay(device.id)


@celery_app.task(name="app.tasks.device_poll.poll_managed_devices")
def poll_managed_devices():
    """Poll all MANAGED devices for port/vlan/endpoint updates."""
    from sqlalchemy import select

    from app.models.device import Device, DeviceStatus

    with _get_sync_session() as db:
        result = db.execute(select(Device).where(Device.status == DeviceStatus.MANAGED))
        devices = result.scalars().all()
        for device in devices:
            poll_device_task.delay(device.id)


def _poll_device(db, device):
    from app.models.device import DeviceProtocol, DeviceStatus

    now = datetime.now(timezone.utc)

    if device.protocol == DeviceProtocol.REST:
        # REST not implemented in Phase 1
        logger.info(f"Device {device.id} uses REST — skipping (Phase 2)")
        return

    driver = None
    try:
        password = decrypt_credential(device.ssh_password_encrypted)
        driver = get_ssh_driver(
            ip=device.ip_addr,
            username=device.ssh_id,
            password=password,
            port=device.ssh_port or 22,
            device_type=device.device_type or "cisco_ios",
        )

        # Collect system info
        info = driver.get_system_info()
        device.uptime = info.uptime or device.uptime
        device.serial_no = info.serial_no or device.serial_no
        device.model = info.model or device.model
        device.sw_version = info.sw_version or device.sw_version
        device.last_polled_at = now
        device.consecutive_failures = 0

        # Transition to MANAGED if all 4 fields collected
        if all([device.uptime, device.serial_no, device.model, device.sw_version]):
            device.status = DeviceStatus.MANAGED

        db.flush()

        # If MANAGED, also collect ports / vlans / endpoints
        if device.status == DeviceStatus.MANAGED:
            _update_ports(db, device, driver, now)
            _update_vlans(db, device, driver, now)
            _update_endpoints(db, device, driver, now)

        db.commit()

    except Exception as exc:
        logger.warning(f"Poll failed for device {device.id}: {exc}")
        device.consecutive_failures = (device.consecutive_failures or 0) + 1
        device.last_polled_at = now

        if device.consecutive_failures >= MAX_PENDING_RETRIES and device.status == DeviceStatus.PENDING:
            device.status = DeviceStatus.ERROR
        elif device.consecutive_failures >= 3 and device.status == DeviceStatus.MANAGED:
            device.status = DeviceStatus.ERROR

        db.commit()

    finally:
        if driver:
            driver.close()


def _update_ports(db, device, driver, now):
    from app.models.device import DevicePort

    db.execute(delete(DevicePort).where(DevicePort.device_id == device.id))
    for p in driver.get_ports():
        db.add(DevicePort(
            device_id=device.id,
            port_name=p.port_name,
            port_status=p.port_status,
            speed=p.speed,
            duplex=p.duplex,
            connected_mac=p.connected_mac,
            connected_ip=p.connected_ip,
            vlan_id=p.vlan_id,
            polled_at=now,
        ))


def _update_vlans(db, device, driver, now):
    from app.models.device import Vlan

    db.execute(delete(Vlan).where(Vlan.device_id == device.id))
    for v in driver.get_vlans():
        db.add(Vlan(
            device_id=device.id,
            vlan_id=v.vlan_id,
            vlan_name=v.vlan_name,
            polled_at=now,
        ))


def _update_endpoints(db, device, driver, now):
    from app.models.device import Endpoint

    db.execute(delete(Endpoint).where(Endpoint.device_id == device.id))
    for e in driver.get_endpoints():
        db.add(Endpoint(
            device_id=device.id,
            mac_addr=e.mac_addr,
            ip_addr=e.ip_addr,
            port_name=e.port_name,
            vlan_id=e.vlan_id,
            polled_at=now,
        ))
