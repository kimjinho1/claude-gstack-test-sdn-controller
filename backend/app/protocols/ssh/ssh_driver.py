import re

from netmiko import ConnectHandler

from app.protocols.base import (
    AbstractProtocolDriver, EndpointInfo, PortInfo, SystemInfo, VlanInfo,
)


class SSHDriver(AbstractProtocolDriver):
    """Netmiko-based SSH driver.
    Phase 1: Cisco IOS/NX-OS/XE + Arista EOS (full port/vlan/traffic parsing)
    Phase 2+: HP ProCurve, Huawei VRP via Netmiko raw + TextFSM
    """

    def __init__(self, ip: str, username: str, password: str, port: int = 22, device_type: str = "cisco_ios"):
        self._device_type = device_type
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
        raw = self._conn.send_command("show version", use_textfsm=True)

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
            # If TextFSM returned all fields, use them
            if uptime and model and sw_version and serial:
                return SystemInfo(uptime=uptime, serial_no=serial, model=model, sw_version=sw_version)
            # Fall through to regex with raw text if some fields are missing
            raw = self._conn.send_command("show version")

        # Fallback: regex parse (Cisco + Arista patterns)
        output = raw if isinstance(raw, str) else ""
        uptime = re.search(r"(?:uptime is|[Uu]ptime:)\s*(.+)", output)
        serial = re.search(r"(?:Processor board ID|Serial number)\s*:?\s*(\S+)", output)
        model = re.search(r"(?:Cisco (\S+) .* \(revision|Model\s*:\s*(\S+)|^(Arista \S+))", output, re.MULTILINE)
        version = re.search(r"(?:Version (\S+)[,\s]|Software Version\s+(\S+)|Software image version:\s+(\S+))", output)
        return SystemInfo(
            uptime=uptime.group(1).strip() if uptime else "",
            serial_no=serial.group(1) if serial else "",
            model=(model.group(1) or model.group(2) or model.group(3)) if model else "",
            sw_version=(version.group(1) or version.group(2) or version.group(3)) if version else "",
        )

    def get_ports(self) -> list[PortInfo]:
        if self._device_type == "arista_eos":
            return self._get_ports_arista()

        # Cisco IOS/NX-OS/XE: TextFSM via show interfaces status
        output = self._conn.send_command("show interfaces status", use_textfsm=True)
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
        """Parse Arista 'show interfaces' + 'show interfaces switchport' for rich port info."""
        raw_ifaces = self._conn.send_command("show interfaces")
        raw_sw = self._conn.send_command("show interfaces switchport")
        switchport_map = self._parse_arista_switchport(raw_sw)

        ports = []
        # Each interface block starts at a non-indented line like "EthernetN is ..."
        blocks = re.split(r'\n(?=\S)', raw_ifaces)
        for block in blocks:
            m = re.match(r'^(\S+)\s+is\s+(up|down|administratively down)', block)
            if not m:
                continue
            port_name = m.group(1)

            admin_down = "administratively down" in block
            line_up = "line protocol is up" in block

            port_status = "UP" if line_up else "DOWN"
            admin_status = "down" if admin_down else "up"

            desc_m = re.search(r'Description:\s*(.+)', block)
            description = desc_m.group(1).strip() if desc_m else None

            hw_m = re.search(r'Hardware is (\S+(?:\s+\S+)?)', block)
            port_type = hw_m.group(1).strip() if hw_m else None

            # Speed: "1Gb/s", "100Mb/s", "10Gb/s"
            speed_m = re.search(r'([\d.]+\s*(?:Gb|Mb|Kb)/s)', block)
            speed = speed_m.group(1).replace(' ', '') if speed_m else None

            duplex_m = re.search(r'(Full|Half)-duplex', block, re.IGNORECASE)
            duplex = (duplex_m.group(1).lower() + "-duplex") if duplex_m else None

            # Byte counters: "N packets input, N bytes"
            rx_m = re.search(r'(\d+) packets input,\s*(\d+) bytes', block)
            tx_m = re.search(r'(\d+) packets output,\s*(\d+) bytes', block)
            rx_bytes = int(rx_m.group(2)) if rx_m else None
            tx_bytes = int(tx_m.group(2)) if tx_m else None

            sw = switchport_map.get(port_name, {})
            vlan_mode = sw.get("mode")
            vlan_id = sw.get("access_vlan") if vlan_mode == "access" else sw.get("native_vlan")
            pvid = sw.get("native_vlan")
            tagged_vlans = sw.get("trunk_vlans")

            ports.append(PortInfo(
                port_name=port_name,
                port_status=port_status,
                admin_status=admin_status,
                description=description,
                port_type=port_type,
                speed=speed,
                duplex=duplex,
                rx_bytes=rx_bytes,
                tx_bytes=tx_bytes,
                vlan_mode=vlan_mode,
                vlan_id=vlan_id,
                pvid=pvid,
                tagged_vlans=tagged_vlans,
            ))
        return ports

    def _parse_arista_switchport(self, text: str) -> dict:
        """Parse 'show interfaces switchport' into {port_name: info_dict}."""
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
            access_vlan = access_m.group(1) if access_m else None

            native_m = re.search(r'Trunking Native Mode VLAN:\s*(\d+)', block)
            native_vlan = native_m.group(1) if native_m else None

            trunk_m = re.search(r'Trunking VLANs Enabled:\s*(.+)', block)
            trunk_vlans = None
            if trunk_m:
                tv = trunk_m.group(1).strip()
                if tv.upper() not in ("ALL", "NONE", ""):
                    trunk_vlans = tv

            result[port_name] = {
                "mode": mode,
                "access_vlan": access_vlan,
                "native_vlan": native_vlan,
                "trunk_vlans": trunk_vlans,
            }
        return result

    def get_vlans(self) -> list[VlanInfo]:
        # Arista: "show vlan" works; Cisco: "show vlan brief"
        cmd = "show vlan" if self._device_type == "arista_eos" else "show vlan brief"
        output = self._conn.send_command(cmd, use_textfsm=True)
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
