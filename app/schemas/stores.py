from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StoreBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    status: str = "active"


class StoreCreate(StoreBase):
    owner_id: int


class StoreUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    status: str | None = None


class StoreRead(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
