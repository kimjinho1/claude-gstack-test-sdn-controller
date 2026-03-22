"""Unit tests for alarm generation logic."""
import pytest
from unittest.mock import MagicMock, call


def _make_device(status="MANAGED", consecutive_failures=0, ip="10.0.0.1"):
    from app.models.device import DeviceStatus

    device = MagicMock()
    device.id = 1
    device.ip_addr = ip
    device.status = DeviceStatus[status]
    device.consecutive_failures = consecutive_failures
    return device


class TestDeviceDownAlarm:
    def test_creates_alarm_at_threshold(self):
        from app.models.alarm import AlarmStatus, AlarmType
        from app.tasks.alarm_check import _check_device_alarms

        device = _make_device("ERROR", consecutive_failures=3)
        db = MagicMock()
        # No existing DEVICE_DOWN alarm
        db.execute.return_value.scalar_one_or_none.return_value = None

        _check_device_alarms(db, device)

        db.add.assert_called_once()
        added_alarm = db.add.call_args[0][0]
        assert added_alarm.alarm_type == AlarmType.DEVICE_DOWN
        assert added_alarm.status == AlarmStatus.OPEN

    def test_no_duplicate_alarm_when_already_open(self):
        from app.models.alarm import Alarm, AlarmStatus, AlarmType
        from app.tasks.alarm_check import _check_device_alarms

        device = _make_device("ERROR", consecutive_failures=5)
        db = MagicMock()
        # Existing DEVICE_DOWN already open
        existing = MagicMock(spec=Alarm)
        db.execute.return_value.scalar_one_or_none.return_value = existing

        _check_device_alarms(db, device)

        db.add.assert_not_called()

    def test_no_alarm_below_threshold(self):
        from app.tasks.alarm_check import _check_device_alarms

        device = _make_device("MANAGED", consecutive_failures=2)
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = None
        db.execute.return_value.scalars.return_value.all.return_value = []

        _check_device_alarms(db, device)

        db.add.assert_not_called()


class TestDeviceUpAlarm:
    def test_creates_device_up_and_resolves_device_down(self):
        from app.models.alarm import Alarm, AlarmStatus, AlarmType
        from app.tasks.alarm_check import _check_device_alarms

        device = _make_device("MANAGED", consecutive_failures=0)
        db = MagicMock()

        # No open DEVICE_DOWN for the threshold check path (failures == 0)
        existing_down_alarm = MagicMock(spec=Alarm)
        existing_down_alarm.status = AlarmStatus.OPEN

        # db.execute returns different things for different calls
        # Call 1: check for existing DEVICE_DOWN (failures < threshold, so skipped)
        # Call 2: find open DEVICE_DOWN alarms to resolve
        db.execute.return_value.scalars.return_value.all.return_value = [existing_down_alarm]

        _check_device_alarms(db, device)

        # DEVICE_DOWN should be resolved
        assert existing_down_alarm.status == AlarmStatus.RESOLVED

        # DEVICE_UP alarm should be created as OPEN (so user sees recovery)
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.alarm_type == AlarmType.DEVICE_UP
        assert added.status == AlarmStatus.OPEN

    def test_no_device_up_when_no_open_down_alarms(self):
        from app.tasks.alarm_check import _check_device_alarms

        device = _make_device("MANAGED", consecutive_failures=0)
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = []

        _check_device_alarms(db, device)

        db.add.assert_not_called()
