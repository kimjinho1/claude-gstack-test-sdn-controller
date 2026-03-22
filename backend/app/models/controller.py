from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeviceModel(Base):
    """Catalog of device models (physical or virtual).
    Users can add/edit/delete models. Each model can optionally have a
    docker_image for spinning up virtual instances.
    """
    __tablename__ = "device_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)          # e.g. "cEOS-lab"
    vendor: Mapped[str] = mapped_column(String(64), nullable=False)          # e.g. "Arista"
    device_type: Mapped[str] = mapped_column(String(32), nullable=False)     # Netmiko device type
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)                      # device photo/icon URL
    docker_image: Mapped[str | None] = mapped_column(String(128))            # e.g. "ceos:latest"
    is_virtual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    virtual_devices: Mapped[list["VirtualDevice"]] = relationship(
        "VirtualDevice", back_populates="model", cascade="all, delete-orphan"
    )


class VirtualDevice(Base):
    """A running (or stopped) virtual device Docker container."""
    __tablename__ = "virtual_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)           # container name
    model_id: Mapped[int] = mapped_column(ForeignKey("device_models.id"), nullable=False)
    container_id: Mapped[str | None] = mapped_column(String(128))            # Docker container ID
    container_ip: Mapped[str | None] = mapped_column(String(45))            # IP on sdn-lab network (use this for polling)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False)           # host port mapped to :22
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="starting")
    # starting | running | stopped | error

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    model: Mapped["DeviceModel"] = relationship("DeviceModel", back_populates="virtual_devices")
