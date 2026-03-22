"""
Per-device-type command registry and parser dispatch.

Each vendor/device-type entry defines which CLI commands to run and
whether to use TextFSM for parsing.  When Netmiko's built-in TextFSM
templates don't cover a platform (e.g. HP ProCurve, Huawei VRP) the
entry sets use_textfsm_* to False and the driver falls back to manual
regex parsing implemented in ssh_driver.py.

device_type values correspond to Netmiko device_type strings AND to
the device_models.device_type column in the database.
"""

from dataclasses import dataclass, field


@dataclass
class DeviceCommands:
    # ── system info ──────────────────────────────────────────────────
    show_version: str = "show version"
    use_textfsm_version: bool = True

    # ── port / interface info ─────────────────────────────────────────
    # For Cisco-style: single 'show interfaces status' with TextFSM
    # For Arista:     'show interfaces' (raw) + 'show interfaces switchport' (raw)
    show_ports: str = "show interfaces status"
    use_textfsm_ports: bool = True
    # If set, parse this for detailed per-port data (ignores show_ports for arista path)
    show_ports_detail: str | None = None
    show_switchport: str | None = None

    # ── VLAN table ────────────────────────────────────────────────────
    show_vlans: str = "show vlan brief"
    use_textfsm_vlans: bool = True

    # ── MAC / endpoint table ──────────────────────────────────────────
    show_mac_table: str = "show mac address-table"
    use_textfsm_mac: bool = True

    # ── running config ────────────────────────────────────────────────
    # None → endpoint returns 501 "not supported on this device type"
    show_running_config: str | None = "show running-config"


# ── Registry ──────────────────────────────────────────────────────────────────

VENDOR_COMMANDS: dict[str, DeviceCommands] = {
    # ── Cisco IOS / IOS-XE ───────────────────────────────────────────
    "cisco_ios": DeviceCommands(
        show_version="show version",
        show_ports="show interfaces status",
        use_textfsm_ports=True,
        show_vlans="show vlan brief",
        show_mac_table="show mac address-table",
        show_running_config="show running-config",
    ),

    # ── Cisco NX-OS ──────────────────────────────────────────────────
    "cisco_nxos": DeviceCommands(
        show_version="show version",
        show_ports="show interface status",
        use_textfsm_ports=True,
        show_vlans="show vlan brief",
        show_mac_table="show mac address-table",
        show_running_config="show running-config",
    ),

    # ── Cisco XR ─────────────────────────────────────────────────────
    "cisco_xr": DeviceCommands(
        show_version="show version",
        show_ports="show interfaces brief",
        use_textfsm_ports=True,
        show_vlans="show vlan",
        show_mac_table="show mac-address-table",
        show_running_config="show running-config",
    ),

    # ── Arista EOS ───────────────────────────────────────────────────
    # Uses raw parsing (not TextFSM) for ports; TextFSM for vlans/mac
    "arista_eos": DeviceCommands(
        show_version="show version",
        use_textfsm_version=True,
        show_ports_detail="show interfaces",        # raw, parsed by _get_ports_arista()
        show_switchport="show interfaces switchport",
        show_vlans="show vlan",
        use_textfsm_vlans=True,
        show_mac_table="show mac address-table",
        use_textfsm_mac=True,
        show_running_config="show running-config",
    ),

    # ── HP / Aruba ProCurve ───────────────────────────────────────────
    # TextFSM templates exist for some ProCurve commands but coverage
    # is spotty — use raw + regex as safe default.
    "hp_procurve": DeviceCommands(
        show_version="show system information",
        use_textfsm_version=False,
        show_ports="show interfaces brief",
        use_textfsm_ports=False,
        show_vlans="show vlans",
        use_textfsm_vlans=False,
        show_mac_table="show mac-address",
        use_textfsm_mac=False,
        show_running_config="show running-config",
    ),

    # ── Huawei VRP ───────────────────────────────────────────────────
    "huawei_vrp": DeviceCommands(
        show_version="display version",
        use_textfsm_version=False,
        show_ports="display interface brief",
        use_textfsm_ports=False,
        show_vlans="display vlan",
        use_textfsm_vlans=False,
        show_mac_table="display mac-address",
        use_textfsm_mac=False,
        show_running_config="display current-configuration",
    ),

    # ── Juniper JunOS ────────────────────────────────────────────────
    "juniper_junos": DeviceCommands(
        show_version="show version",
        use_textfsm_version=True,
        show_ports="show interfaces terse",
        use_textfsm_ports=True,
        show_vlans="show vlans",
        use_textfsm_vlans=True,
        show_mac_table="show ethernet-switching table",
        use_textfsm_mac=True,
        show_running_config="show configuration",
    ),
}

# Default fallback for unknown device types
_DEFAULT = DeviceCommands()


def get_commands(device_type: str) -> DeviceCommands:
    """Return the DeviceCommands for the given netmiko device_type."""
    return VENDOR_COMMANDS.get(device_type, _DEFAULT)
