import re

from netmiko import ConnectHandler

from app.protocols.base import (
    AbstractProtocolDriver, EndpointInfo, PortInfo, SystemInfo, VlanInfo,
)
from app.protocols.ssh.vendor_commands import DeviceCommands, get_commands


def _is_cli_error(output: str) -> bool:
    """Return True when the device returned a CLI error line (% …)."""
    for line in output.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("%"):
            return True
    return False


class SSHDriver(AbstractProtocolDriver):
    """
    Netmiko-based SSH driver with per-device-type command dispatch.

    Commands and TextFSM usage are looked up from vendor_commands.py
    so that new vendors can be added without touching this file.

    Device type → driver dispatch:
      arista_eos  → _get_ports_arista()  (raw regex, no TextFSM)
      hp_procurve → _get_ports_hp()      (raw regex)
      huawei_vrp  → _get_ports_huawei()  (raw regex)
      *           → _get_ports_textfsm() (TextFSM / Cisco-style)
    """

    def __init__(self, ip: str, username: str, password: str, port: int = 22, device_type: str = "cisco_ios"):
        self._device_type = device_type
        self._cmds: DeviceCommands = get_commands(device_type)
        self._conn = ConnectHandler(
            device_type=device_type,
            host=ip,
            username=username,
            password=password,
            port=port,
            timeout=10,
            session_timeout=15,
        )

    # ── System info ───────────────────────────────────────────────────────────

    def get_system_info(self) -> SystemInfo:
        raw = self._conn.send_command(
            self._cmds.show_version,
            use_textfsm=self._cmds.use_textfsm_version,
        )

        # Huawei / HP — raw text, manual parse
        if self._device_type in ("huawei_vrp", "hp_procurve"):
            return self._parse_system_info_raw(raw if isinstance(raw, str) else "")

        # Cisco / Arista TextFSM path
        if isinstance(raw, list) and raw:
            d = raw[0]
            uptime = d.get("uptime", "")
            serial = d.get("serial", "")
            if isinstance(serial, list):
                serial = serial[0] if serial else ""
            hardware = d.get("hardware", "")
            if isinstance(hardware, list):
                hardware = hardware[0] if hardware else ""
            model = hardware or d.get("model", "")
            sw_version = d.get("version", "")
            if uptime and model and sw_version and serial:
                return SystemInfo(uptime=uptime, serial_no=serial, model=model, sw_version=sw_version)
            # Fall through to regex if fields are missing
            raw = self._conn.send_command(self._cmds.show_version)

        return self._parse_system_info_raw(raw if isinstance(raw, str) else "")

    def _parse_system_info_raw(self, output: str) -> SystemInfo:
        """Generic regex fallback for system info (works for Cisco/Arista/Huawei/HP)."""
        uptime = re.search(r"(?:uptime is|[Uu]ptime:|[Uu]ptime)\s*(.+)", output)
        serial = re.search(r"(?:Processor board ID|Serial number|[Ss]erial\s*[Nn]o\.?)\s*:?\s*(\S+)", output)
        model = re.search(
            r"(?:Cisco (\S+) .* \(revision|Model\s*:\s*(\S+)|^(Arista \S+)|"
            r"Huawei (\S+) Versatile|HP (\S+) Switch)",
            output, re.MULTILINE,
        )
        version = re.search(
            r"(?:Version (\S+)[,\s]|Software Version\s+(\S+)|"
            r"Software image version:\s+(\S+)|VRP.*Version (\S+))",
            output,
        )
        groups = lambda m: next((g for g in m.groups() if g), "") if m else ""
        return SystemInfo(
            uptime=uptime.group(1).strip() if uptime else "",
            serial_no=groups(serial),
            model=groups(model),
            sw_version=groups(version),
        )

    # ── Ports ─────────────────────────────────────────────────────────────────

    def get_ports(self) -> list[PortInfo]:
        if self._device_type == "arista_eos":
            return self._get_ports_arista()
        if self._device_type == "hp_procurve":
            return self._get_ports_hp()
        if self._device_type == "huawei_vrp":
            return self._get_ports_huawei()
        return self._get_ports_textfsm()

    def _get_ports_textfsm(self) -> list[PortInfo]:
        """Cisco IOS/NX-OS/XE — TextFSM via show interfaces status."""
        output = self._conn.send_command(
            self._cmds.show_ports,
            use_textfsm=self._cmds.use_textfsm_ports,
        )
        ports = []
        if isinstance(output, list):
            for row in output:
                ports.append(PortInfo(
                    port_name=row.get("port", ""),
                    port_status="UP" if "connected" in str(row.get("status", "")).lower() else "DOWN",
                    speed=str(row.get("speed", "")),
                    duplex=str(row.get("duplex", "")),
                    vlan_id=str(row.get("vlan", "")) if row.get("vlan") else None,
                ))
        return ports

    def _get_ports_arista(self) -> list[PortInfo]:
        """Arista EOS — raw 'show interfaces' + 'show interfaces switchport'."""
        cmd_detail = self._cmds.show_ports_detail or "show interfaces"
        cmd_sw = self._cmds.show_switchport or "show interfaces switchport"

        raw_ifaces = self._conn.send_command(cmd_detail)
        raw_sw = self._conn.send_command(cmd_sw)
        switchport_map = self._parse_arista_switchport(raw_sw)

        ports = []
        blocks = re.split(r'\n(?=\S)', raw_ifaces)
        for block in blocks:
            m = re.match(r'^(\S+)\s+is\s+(up|down|administratively down)', block)
            if not m:
                continue
            port_name = m.group(1)
            admin_down = "administratively down" in block
            line_up = "line protocol is up" in block

            desc_m = re.search(r'Description:\s*(.+)', block)
            hw_m = re.search(r'Hardware is (\S+(?:\s+\S+)?)', block)
            speed_m = re.search(r'([\d.]+\s*(?:Gb|Mb|Kb)/s)', block)
            duplex_m = re.search(r'(Full|Half)-duplex', block, re.IGNORECASE)
            rx_m = re.search(r'(\d+) packets input,\s*(\d+) bytes', block)
            tx_m = re.search(r'(\d+) packets output,\s*(\d+) bytes', block)

            sw = switchport_map.get(port_name, {})
            vlan_mode = sw.get("mode")
            vlan_id = sw.get("access_vlan") if vlan_mode == "access" else sw.get("native_vlan")

            ports.append(PortInfo(
                port_name=port_name,
                port_status="UP" if line_up else "DOWN",
                admin_status="down" if admin_down else "up",
                description=desc_m.group(1).strip() if desc_m else None,
                port_type=hw_m.group(1).strip() if hw_m else None,
                speed=speed_m.group(1).replace(' ', '') if speed_m else None,
                duplex=(duplex_m.group(1).lower() + "-duplex") if duplex_m else None,
                rx_bytes=int(rx_m.group(2)) if rx_m else None,
                tx_bytes=int(tx_m.group(2)) if tx_m else None,
                vlan_mode=vlan_mode,
                vlan_id=vlan_id,
                pvid=sw.get("native_vlan"),
                tagged_vlans=sw.get("trunk_vlans"),
            ))
        return ports

    def _parse_arista_switchport(self, text: str) -> dict:
        result = {}
        blocks = re.split(r'(?=^Name:)', text, flags=re.MULTILINE)
        for block in blocks:
            if not block.strip():
                continue
            name_m = re.match(r'Name:\s*(\S+)', block)
            if not name_m:
                continue
            port_name = name_m.group(1)
            mode_m = re.search(r'Operational Mode:\s*(\S+)', block)
            mode = mode_m.group(1).lower() if mode_m else None
            access_m = re.search(r'Access Mode VLAN:\s*(\d+)', block)
            native_m = re.search(r'Trunking Native Mode VLAN:\s*(\d+)', block)
            trunk_m = re.search(r'Trunking VLANs Enabled:\s*(.+)', block)
            trunk_vlans = None
            if trunk_m:
                tv = trunk_m.group(1).strip()
                if tv.upper() not in ("ALL", "NONE", ""):
                    trunk_vlans = tv
            result[port_name] = {
                "mode": mode,
                "access_vlan": access_m.group(1) if access_m else None,
                "native_vlan": native_m.group(1) if native_m else None,
                "trunk_vlans": trunk_vlans,
            }
        return result

    def _get_ports_hp(self) -> list[PortInfo]:
        """HP ProCurve — raw 'show interfaces brief' regex parsing."""
        output = self._conn.send_command(self._cmds.show_ports)
        ports = []
        # Example line: " 1     100TX  1000FDx  Yes    No  Enabled   0"
        for line in output.splitlines():
            m = re.match(
                r'^\s*(\S+)\s+(\S+)\s+(\S+)\s+(Yes|No)\s+(Yes|No)\s+(Enabled|Disabled)\s*',
                line, re.IGNORECASE,
            )
            if not m:
                continue
            port_name, port_type, speed_duplex, link, intrusion, admin = m.groups()
            port_status = "UP" if link.lower() == "yes" else "DOWN"
            admin_status = "up" if admin.lower() == "enabled" else "down"
            # speed_duplex like "1000FDx" or "100HDx"
            speed_m = re.match(r'(\d+)(FDx|HDx|auto)', speed_duplex, re.IGNORECASE)
            speed = speed_m.group(1) + "Mbps" if speed_m else None
            duplex = ("full-duplex" if speed_m and "FD" in speed_m.group(2).upper()
                      else "half-duplex" if speed_m else None)
            ports.append(PortInfo(
                port_name=port_name,
                port_status=port_status,
                admin_status=admin_status,
                port_type=port_type,
                speed=speed,
                duplex=duplex,
            ))
        return ports

    def _get_ports_huawei(self) -> list[PortInfo]:
        """Huawei VRP — raw 'display interface brief' regex parsing."""
        output = self._conn.send_command(self._cmds.show_ports)
        ports = []
        # Example line: "GigabitEthernet0/0/1    up      up       1000M   full  --"
        for line in output.splitlines():
            m = re.match(
                r'^(\S+)\s+(up|down|*)\s+(up|down)\s+(\S+)\s+(full|half|-+)\s*(.*)$',
                line, re.IGNORECASE,
            )
            if not m:
                continue
            port_name, phy_status, proto_status, speed_str, duplex_str, desc = m.groups()
            port_status = "UP" if proto_status.lower() == "up" else "DOWN"
            admin_status = "up" if phy_status.lower() != "down" else "down"
            ports.append(PortInfo(
                port_name=port_name,
                port_status=port_status,
                admin_status=admin_status,
                speed=speed_str if speed_str != "--" else None,
                duplex=duplex_str + "-duplex" if duplex_str not in ("-", "--") else None,
                description=desc.strip() if desc.strip() else None,
            ))
        return ports

    # ── VLANs ─────────────────────────────────────────────────────────────────

    def get_vlans(self) -> list[VlanInfo]:
        output = self._conn.send_command(
            self._cmds.show_vlans,
            use_textfsm=self._cmds.use_textfsm_vlans,
        )
        vlans = []

        if self._device_type == "huawei_vrp":
            return self._parse_vlans_huawei(output if isinstance(output, str) else "")
        if self._device_type == "hp_procurve":
            return self._parse_vlans_hp(output if isinstance(output, str) else "")

        # TextFSM path (Cisco / Arista / Juniper)
        if isinstance(output, list):
            for row in output:
                vlans.append(VlanInfo(
                    vlan_id=str(row.get("vlan_id", "")),
                    vlan_name=row.get("name"),
                ))
        return vlans

    def _parse_vlans_huawei(self, text: str) -> list[VlanInfo]:
        vlans = []
        for m in re.finditer(r'^VLAN\s+(\d+)\s+.*?Name:\s*(\S+)', text, re.MULTILINE | re.DOTALL):
            vlans.append(VlanInfo(vlan_id=m.group(1), vlan_name=m.group(2)))
        return vlans

    def _parse_vlans_hp(self, text: str) -> list[VlanInfo]:
        vlans = []
        # "VLAN 1  Name DEFAULT_VLAN  ..."
        for m in re.finditer(r'VLAN\s+(\d+)\s+Name\s+(\S+)', text, re.IGNORECASE):
            vlans.append(VlanInfo(vlan_id=m.group(1), vlan_name=m.group(2)))
        return vlans

    # ── Endpoints (MAC table) ─────────────────────────────────────────────────

    def get_endpoints(self) -> list[EndpointInfo]:
        output = self._conn.send_command(
            self._cmds.show_mac_table,
            use_textfsm=self._cmds.use_textfsm_mac,
        )
        endpoints = []

        if self._device_type in ("huawei_vrp", "hp_procurve"):
            return self._parse_mac_raw(
                output if isinstance(output, str) else "",
                huawei=(self._device_type == "huawei_vrp"),
            )

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

    def _parse_mac_raw(self, text: str, huawei: bool = False) -> list[EndpointInfo]:
        endpoints = []
        if huawei:
            # "0001-0001-0001  1       GE0/0/1  dynamic"
            pattern = r'([\da-fA-F]{4}-[\da-fA-F]{4}-[\da-fA-F]{4})\s+(\d+)\s+(\S+)'
        else:
            # HP: "000000-000001  1       1"
            pattern = r'([\da-fA-F]{6}-[\da-fA-F]{6})\s+(\d+)\s+(\S+)'
        for m in re.finditer(pattern, text):
            endpoints.append(EndpointInfo(
                mac_addr=m.group(1),
                ip_addr=None,
                port_name=m.group(3),
                vlan_id=m.group(2),
            ))
        return endpoints

    # ── Running config ────────────────────────────────────────────────────────

    def get_running_config(self) -> str:
        cmd = self._cmds.show_running_config
        if cmd is None:
            raise RuntimeError(
                f"running-config 조회가 {self._device_type} 장비에서 지원되지 않습니다."
            )
        output = self._conn.send_command(cmd)
        # Detect CLI error responses (lines starting with %)
        if _is_cli_error(output):
            first_err = next(
                l.strip() for l in output.splitlines() if l.strip().startswith("%")
            )
            raise RuntimeError(
                f"장비가 명령어를 거부했습니다 ({self._device_type}): {first_err}"
            )
        return output

    def close(self):
        self._conn.disconnect()


def get_ssh_driver(ip: str, username: str, password: str, port: int = 22, device_type: str = "cisco_ios") -> SSHDriver:
    return SSHDriver(ip=ip, username=username, password=password, port=port, device_type=device_type)
