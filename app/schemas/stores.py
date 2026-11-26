from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import StoreStatus

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class StoreBase(BaseModel):
    name: str
    slug: str = Field(pattern=SLUG_PATTERN)
    description: str | None = None
    status: StoreStatus = StoreStatus.ACTIVE


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: str | None = None
    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)
    description: str | None = None
    status: StoreStatus | None = None


class StoreRead(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
