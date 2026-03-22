import re

from netmiko import ConnectHandler, NetmikoAuthenticationException, NetmikoTimeoutException

from app.protocols.base import (
    AbstractProtocolDriver, EndpointInfo, PortInfo, SystemInfo, VlanInfo,
)


class SSHDriver(AbstractProtocolDriver):
    """Netmiko-based SSH driver for Cisco IOS/NX-OS (Phase 1).
    Phase 2 will add HP ProCurve, Huawei VRP via Netmiko raw + TextFSM."""

    DEVICE_TYPE_MAP = {
        "cisco_ios": "cisco_ios",
        "cisco_nxos": "cisco_nxos",
        "cisco_xe": "cisco_xe",
    }

    def __init__(self, ip: str, username: str, password: str, port: int = 22, device_type: str = "cisco_ios"):
        self._conn = ConnectHandler(
            device_type=device_type,
            host=ip,
            username=username,
            password=password,
            port=port,
            timeout=10,
            session_timeout=15,
        )

    def get_system_info(self) -> SystemInfo:
        output = self._conn.send_command("show version", use_textfsm=True)

        if isinstance(output, list) and output:
            d = output[0]
            return SystemInfo(
                uptime=d.get("uptime", ""),
                serial_no=d.get("serial", [""])[0] if isinstance(d.get("serial"), list) else d.get("serial", ""),
                model=d.get("hardware", [""])[0] if isinstance(d.get("hardware"), list) else d.get("hardware", ""),
                sw_version=d.get("version", ""),
            )

        # Fallback: regex parse
        uptime = re.search(r"uptime is (.+)", output or "")
        serial = re.search(r"Processor board ID (\S+)", output or "")
        model = re.search(r"Cisco (\S+) .* \(revision", output or "")
        version = re.search(r"Version (\S+),", output or "")
        return SystemInfo(
            uptime=uptime.group(1) if uptime else "",
            serial_no=serial.group(1) if serial else "",
            model=model.group(1) if model else "",
            sw_version=version.group(1) if version else "",
        )

    def get_ports(self) -> list[PortInfo]:
        output = self._conn.send_command("show interfaces status", use_textfsm=True)
        ports = []
        if isinstance(output, list):
            for row in output:
                ports.append(PortInfo(
                    port_name=row.get("port", ""),
                    port_status="UP" if "connected" in str(row.get("status", "")).lower() else "DOWN",
                    speed=str(row.get("speed", "")),
                    duplex=str(row.get("duplex", "")),
                    connected_mac=None,
                    connected_ip=None,
                    vlan_id=str(row.get("vlan", "")) if row.get("vlan") else None,
                ))
        return ports

    def get_vlans(self) -> list[VlanInfo]:
        output = self._conn.send_command("show vlan brief", use_textfsm=True)
        vlans = []
        if isinstance(output, list):
            for row in output:
                vlans.append(VlanInfo(
                    vlan_id=str(row.get("vlan_id", "")),
                    vlan_name=row.get("name"),
                ))
        return vlans

    def get_endpoints(self) -> list[EndpointInfo]:
        output = self._conn.send_command("show mac address-table", use_textfsm=True)
        endpoints = []
        if isinstance(output, list):
            for row in output:
                mac = row.get("destination_address") or row.get("mac")
                if not mac:
                    continue
                endpoints.append(EndpointInfo(
                    mac_addr=mac,
                    ip_addr=None,
                    port_name=row.get("destination_port") or row.get("ports"),
                    vlan_id=str(row.get("vlan", "")),
                ))
        return endpoints

    def close(self):
        self._conn.disconnect()


def get_ssh_driver(ip: str, username: str, password: str, port: int = 22, device_type: str = "cisco_ios") -> SSHDriver:
    return SSHDriver(ip=ip, username=username, password=password, port=port, device_type=device_type)
