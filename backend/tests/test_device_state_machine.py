"""Unit tests for device status state machine logic in _poll_device."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def _make_device(status="PENDING", consecutive_failures=0):
    from app.models.device import DeviceProtocol, DeviceStatus

    device = MagicMock()
    device.id = 1
    device.ip_addr = "10.0.0.1"
    device.protocol = DeviceProtocol.SSH
    device.ssh_id = "admin"
    device.ssh_password_encrypted = "encrypted"
    device.ssh_port = 22
    device.device_type = "cisco_ios"
    device.status = DeviceStatus[status]
    device.consecutive_failures = consecutive_failures
    device.uptime = None
    device.serial_no = None
    device.model = None
    device.sw_version = None
    device.last_polled_at = None
    return device


def _make_system_info(uptime="5 days", serial="SN001", model="WS-C2960", sw_version="15.2"):
    from app.protocols.base import SystemInfo
    return SystemInfo(uptime=uptime, serial_no=serial, model=model, sw_version=sw_version)


class TestPendingToManaged:
    def test_all_four_fields_collected_transitions_to_managed(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import _poll_device

        device = _make_device("PENDING")
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", return_value="pass"), \
             patch("app.tasks.device_poll.get_ssh_driver") as mock_driver_fn:
            mock_driver = MagicMock()
            mock_driver.get_system_info.return_value = _make_system_info()
            mock_driver.get_ports.return_value = []
            mock_driver.get_vlans.return_value = []
            mock_driver.get_endpoints.return_value = []
            mock_driver_fn.return_value = mock_driver

            _poll_device(db, device)

        assert device.status == DeviceStatus.MANAGED
        assert device.consecutive_failures == 0
        mock_driver.close.assert_called_once()

    def test_missing_one_field_stays_pending(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import _poll_device

        device = _make_device("PENDING")
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", return_value="pass"), \
             patch("app.tasks.device_poll.get_ssh_driver") as mock_driver_fn:
            mock_driver = MagicMock()
            # sw_version is empty → cannot transition
            mock_driver.get_system_info.return_value = _make_system_info(sw_version="")
            mock_driver_fn.return_value = mock_driver

            _poll_device(db, device)

        assert device.status == DeviceStatus.PENDING

    def test_ten_failures_transitions_pending_to_error(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import MAX_PENDING_RETRIES, _poll_device

        device = _make_device("PENDING", consecutive_failures=MAX_PENDING_RETRIES - 1)
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", side_effect=Exception("SSH failed")):
            _poll_device(db, device)

        assert device.status == DeviceStatus.ERROR
        assert device.consecutive_failures == MAX_PENDING_RETRIES


class TestManagedToError:
    def test_three_consecutive_failures_transitions_to_error(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import _poll_device

        device = _make_device("MANAGED", consecutive_failures=2)
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", side_effect=Exception("timeout")):
            _poll_device(db, device)

        assert device.status == DeviceStatus.ERROR
        assert device.consecutive_failures == 3

    def test_two_failures_stays_managed(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import _poll_device

        device = _make_device("MANAGED", consecutive_failures=1)
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", side_effect=Exception("timeout")):
            _poll_device(db, device)

        assert device.status == DeviceStatus.MANAGED
        assert device.consecutive_failures == 2


class TestErrorRecovery:
    def test_successful_poll_error_to_managed(self):
        from app.models.device import DeviceStatus
        from app.tasks.device_poll import _poll_device

        device = _make_device("ERROR", consecutive_failures=5)
        device.uptime = "old"
        device.serial_no = "SN001"
        device.model = "WS"
        device.sw_version = "15"
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", return_value="pass"), \
             patch("app.tasks.device_poll.get_ssh_driver") as mock_driver_fn:
            mock_driver = MagicMock()
            mock_driver.get_system_info.return_value = _make_system_info()
            mock_driver.get_ports.return_value = []
            mock_driver.get_vlans.return_value = []
            mock_driver.get_endpoints.return_value = []
            mock_driver_fn.return_value = mock_driver

            _poll_device(db, device)

        assert device.status == DeviceStatus.MANAGED
        assert device.consecutive_failures == 0


class TestSSHConnectionCleanup:
    def test_driver_closed_even_on_exception_after_creation(self):
        """SSH connection must be closed even if an exception occurs after driver creation."""
        from app.tasks.device_poll import _poll_device

        device = _make_device("MANAGED")
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", return_value="pass"), \
             patch("app.tasks.device_poll.get_ssh_driver") as mock_driver_fn:
            mock_driver = MagicMock()
            # Simulate exception after driver creation but before commit
            mock_driver.get_system_info.side_effect = Exception("connection reset")
            mock_driver_fn.return_value = mock_driver

            _poll_device(db, device)

        mock_driver.close.assert_called_once()

    def test_driver_closed_on_happy_path(self):
        from app.tasks.device_poll import _poll_device

        device = _make_device("PENDING")
        db = MagicMock()

        with patch("app.tasks.device_poll.decrypt_credential", return_value="pass"), \
             patch("app.tasks.device_poll.get_ssh_driver") as mock_driver_fn:
            mock_driver = MagicMock()
            mock_driver.get_system_info.return_value = _make_system_info()
            mock_driver.get_ports.return_value = []
            mock_driver.get_vlans.return_value = []
            mock_driver.get_endpoints.return_value = []
            mock_driver_fn.return_value = mock_driver

            _poll_device(db, device)

        mock_driver.close.assert_called_once()
