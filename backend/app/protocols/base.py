from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SystemInfo:
    uptime: str
    serial_no: str
    model: str
    sw_version: str


@dataclass
class PortInfo:
    port_name: str
    port_status: str                  # "UP" or "DOWN" (line protocol)
    admin_status: str | None = None   # "up" (no shutdown) or "down" (shutdown)
    description: str | None = None
    port_type: str | None = None      # e.g. "1000BASE-T", "SFP+"
    speed: str | None = None
    duplex: str | None = None
    connected_mac: str | None = None
    connected_ip: str | None = None
    vlan_mode: str | None = None      # "access" or "trunk"
    vlan_id: str | None = None        # access VLAN or native VLAN
    pvid: str | None = None
    tagged_vlans: str | None = None   # comma-separated e.g. "10,20,30"
    rx_bytes: int | None = None
    tx_bytes: int | None = None


@dataclass
class VlanInfo:
    vlan_id: str
    vlan_name: str | None


@dataclass
class EndpointInfo:
    mac_addr: str
    ip_addr: str | None
    port_name: str | None
    vlan_id: str | None


class AbstractProtocolDriver(ABC):
    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        pass

    @abstractmethod
    def get_ports(self) -> list[PortInfo]:
        pass

    @abstractmethod
    def get_vlans(self) -> list[VlanInfo]:
        pass

    @abstractmethod
    def get_endpoints(self) -> list[EndpointInfo]:
        pass

    @abstractmethod
    def close(self):
        pass
