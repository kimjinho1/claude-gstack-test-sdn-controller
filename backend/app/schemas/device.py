import re
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from app.models.device import DeviceProtocol, DeviceStatus

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_IP_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
)

# Netmiko device types supported in Phase 1 (SSH only)
SSH_DEVICE_TYPES = {"cisco_ios", "cisco_nxos", "cisco_xe"}


class DeviceCreate(BaseModel):
    name: str
    mac_addr: str
    ip_addr: str
    site_id: int
    building_id: int
    floor: int | None = None
    protocol: DeviceProtocol
    device_type: str = "cisco_ios"

    # SSH fields
    ssh_id: str | None = None
    ssh_password: str | None = None
    ssh_port: int = 22

    # REST fields
    rest_id: str | None = None
    rest_password: str | None = None
    rest_port: int | None = None

    @field_validator("mac_addr")
    @classmethod
    def validate_mac(cls, v: str) -> str:
        if not _MAC_RE.match(v):
            raise ValueError("mac_addr must be in AA:BB:CC:DD:EE:FF format")
        return v.upper()

    @field_validator("ip_addr")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not _IP_RE.match(v):
            raise ValueError("ip_addr must be a valid IPv4 address (e.g. 10.0.1.1)")
        return v

    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        if v not in SSH_DEVICE_TYPES:
            raise ValueError(f"device_type must be one of: {', '.join(sorted(SSH_DEVICE_TYPES))}")
        return v

    @model_validator(mode="after")
    def validate_protocol_fields(self):
        if self.protocol == DeviceProtocol.SSH:
            if not self.ssh_id or not self.ssh_password:
                raise ValueError("SSH protocol requires ssh_id and ssh_password")
        elif self.protocol == DeviceProtocol.REST:
            if not self.rest_id or not self.rest_password or not self.rest_port:
                raise ValueError("REST protocol requires rest_id, rest_password, and rest_port")
        return self


class DeviceUpdate(BaseModel):
    name: str | None = None
    floor: int | None = None
    ssh_id: str | None = None
    ssh_password: str | None = None
    ssh_port: int | None = None
    rest_id: str | None = None
    rest_password: str | None = None
    rest_port: int | None = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    mac_addr: str
    ip_addr: str
    site_id: int
    building_id: int
    floor: int | None
    protocol: DeviceProtocol
    device_type: str
    status: DeviceStatus
    uptime: str | None
    serial_no: str | None
    model: str | None
    sw_version: str | None
    last_polled_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortResponse(BaseModel):
    id: int
    port_name: str
    port_status: str
    speed: str | None
    duplex: str | None
    connected_mac: str | None
    connected_ip: str | None
    vlan_id: str | None
    polled_at: datetime | None

    model_config = {"from_attributes": True}


class VlanResponse(BaseModel):
    id: int
    vlan_id: str
    vlan_name: str | None
    polled_at: datetime | None

    model_config = {"from_attributes": True}


class EndpointResponse(BaseModel):
    id: int
    mac_addr: str
    ip_addr: str | None
    port_name: str | None
    vlan_id: str | None
    polled_at: datetime | None

    model_config = {"from_attributes": True}
