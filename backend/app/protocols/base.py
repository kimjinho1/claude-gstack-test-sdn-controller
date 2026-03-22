from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SystemInfo:
    uptime: str
    serial_no: str
    model: str
    sw_version: str


@dataclass
class PortInfo:
    port_name: str
    port_status: str  # "UP" or "DOWN"
    speed: str | None
    duplex: str | None
    connected_mac: str | None
    connected_ip: str | None
    vlan_id: str | None


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
