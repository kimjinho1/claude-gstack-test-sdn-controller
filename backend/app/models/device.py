from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeviceProtocol(str, PyEnum):
    SSH = "SSH"
    REST = "REST"


class DeviceStatus(str, PyEnum):
    UNREGISTERED = "UNREGISTERED"
    PENDING = "PENDING"
    MANAGED = "MANAGED"
    ERROR = "ERROR"


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mac_addr: Mapped[str] = mapped_column(String(17), nullable=False)
    ip_addr: Mapped[str] = mapped_column(String(45), nullable=False)

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)

    protocol: Mapped[DeviceProtocol] = mapped_column(Enum(DeviceProtocol), nullable=False)
    # Netmiko device type — determines SSH command parsing.
    # Phase 1 supports: cisco_ios, cisco_nxos, cisco_xe
    # Phase 2+:         hp_procurve, huawei_vrp
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, default="cisco_ios")

    # Optional FK to device_models catalog (nullable — legacy devices may not have one)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("device_models.id", ondelete="SET NULL"), nullable=True, index=True)

    # SSH credentials (encrypted, non-null only when protocol=SSH)
    ssh_id: Mapped[str | None] = mapped_column(String(128))
    ssh_password_encrypted: Mapped[str | None] = mapped_column(Text)
    ssh_port: Mapped[int | None] = mapped_column(Integer, default=22)

    # REST credentials (encrypted, non-null only when protocol=REST)
    rest_id: Mapped[str | None] = mapped_column(String(128))
    rest_password_encrypted: Mapped[str | None] = mapped_column(Text)
    rest_port: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), nullable=False, default=DeviceStatus.PENDING
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Collected device info (all must be non-NULL for MANAGED status)
    uptime: Mapped[str | None] = mapped_column(String(128))
    serial_no: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    sw_version: Mapped[str | None] = mapped_column(String(128))

    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    building: Mapped["Building"] = relationship("Building", back_populates="devices")
    ports: Mapped[list["DevicePort"]] = relationship("DevicePort", back_populates="device", cascade="all, delete-orphan")
    vlans: Mapped[list["Vlan"]] = relationship("Vlan", back_populates="device", cascade="all, delete-orphan")
    endpoints: Mapped[list["Endpoint"]] = relationship("Endpoint", back_populates="device", cascade="all, delete-orphan")
    alarms: Mapped[list["Alarm"]] = relationship("Alarm", back_populates="device")


class DeviceLink(Base):
    """Parent-child link between devices for topology visualization."""

    __tablename__ = "device_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("parent_id", "child_id", name="uq_device_link"),)


class DevicePort(Base):
    __tablename__ = "device_ports"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    port_name: Mapped[str] = mapped_column(String(64), nullable=False)
    port_status: Mapped[str] = mapped_column(String(16))        # UP / DOWN (line protocol)
    admin_status: Mapped[str | None] = mapped_column(String(16))  # up / down (admin — shutdown or not)
    description: Mapped[str | None] = mapped_column(String(255))
    port_type: Mapped[str | None] = mapped_column(String(64))   # e.g. "1000BASE-T", "SFP+"
    speed: Mapped[str | None] = mapped_column(String(32))
    duplex: Mapped[str | None] = mapped_column(String(16))
    connected_mac: Mapped[str | None] = mapped_column(String(17))
    connected_ip: Mapped[str | None] = mapped_column(String(45))
    # VLAN switchport info
    vlan_mode: Mapped[str | None] = mapped_column(String(16))   # access / trunk
    vlan_id: Mapped[str | None] = mapped_column(String(16))     # access VLAN or native VLAN
    pvid: Mapped[str | None] = mapped_column(String(16))        # native/untagged VLAN
    tagged_vlans: Mapped[str | None] = mapped_column(String(512))  # comma-separated e.g. "10,20,30"
    # Traffic counters (raw bytes from device — used to calculate bps)
    rx_bytes: Mapped[int | None] = mapped_column(BigInteger)
    tx_bytes: Mapped[int | None] = mapped_column(BigInteger)
    traffic_in_bps: Mapped[float | None] = mapped_column(Float)
    traffic_out_bps: Mapped[float | None] = mapped_column(Float)
    polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped["Device"] = relationship("Device", back_populates="ports")


class Vlan(Base):
    __tablename__ = "vlans"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    vlan_id: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "10", "200"
    vlan_name: Mapped[str | None] = mapped_column(String(64))
    polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped["Device"] = relationship("Device", back_populates="vlans")


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    mac_addr: Mapped[str] = mapped_column(String(17), nullable=False)
    ip_addr: Mapped[str | None] = mapped_column(String(45))
    port_name: Mapped[str | None] = mapped_column(String(64))
    vlan_id: Mapped[str | None] = mapped_column(String(16))
    polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped["Device"] = relationship("Device", back_populates="endpoints")
