from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = 1


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemRead(CartItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int


class CartBase(BaseModel):
    status: str = "active"


class CartCreate(CartBase):
    pass


class CartUpdate(BaseModel):
    status: str | None = None


class CartRead(CartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    items: list[CartItemRead] = []
