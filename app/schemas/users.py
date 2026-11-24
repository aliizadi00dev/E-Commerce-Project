from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AddressBase(BaseModel):
    street: str
    city: str
    country: str
    postal_code: str
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    street: str | None = None
    city: str | None = None
    country: str | None = None
    postal_code: str | None = None
    is_default: bool | None = None


class AddressRead(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
