from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BuildingResponse(BaseModel):
    id: int
    site_id: int
    name: str
    floors: int
    device_count: int = 0

    model_config = {"from_attributes": True}


class SiteResponse(BaseModel):
    id: int
    group_id: int
    name: str
    description: str | None
    buildings: list[BuildingResponse] = []

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sites: list[SiteResponse] = []

    model_config = {"from_attributes": True}


class SiteCreate(BaseModel):
    group_id: int
    name: str
    description: str | None = None


class SiteUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    group_id: int | None = None  # allow moving site to a different group


class BuildingCreate(BaseModel):
    site_id: int
    name: str
    floors: int = 1


class BuildingUpdate(BaseModel):
    name: str | None = None
    floors: int | None = None
    site_id: int | None = None  # allow moving building to a different site
