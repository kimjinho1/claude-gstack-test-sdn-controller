from datetime import datetime

from pydantic import BaseModel, Field


class DeviceModelCreate(BaseModel):
    name: str
    vendor: str
    device_type: str
    description: str | None = None
    image_url: str | None = None
    docker_image: str | None = None
    is_virtual: bool = False


class DeviceModelUpdate(BaseModel):
    name: str | None = None
    vendor: str | None = None
    device_type: str | None = None
    description: str | None = None
    image_url: str | None = None
    docker_image: str | None = None
    is_virtual: bool | None = None


class DeviceModelResponse(BaseModel):
    id: int
    name: str
    vendor: str
    device_type: str
    description: str | None
    image_url: str | None
    docker_image: str | None
    is_virtual: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VirtualDeviceLaunch(BaseModel):
    name: str
    model_id: int
    ssh_port: int = Field(default=2222, ge=1024, le=65535)


class VirtualDeviceResponse(BaseModel):
    id: int
    name: str
    model_id: int
    container_id: str | None
    ssh_port: int
    status: str
    created_at: datetime
    stopped_at: datetime | None

    model_config = {"from_attributes": True}
