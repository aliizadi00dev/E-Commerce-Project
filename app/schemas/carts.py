from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CartStatus


class CartItemBase(BaseModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemRead(CartItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cart_id: int


class CartBase(BaseModel):
    status: CartStatus = CartStatus.ACTIVE


class CartCreate(CartBase):
    pass


class CartUpdate(BaseModel):
    status: CartStatus | None = None


class CartRead(CartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    total_amount: Decimal = Decimal("0.00")
    items: list[CartItemRead] = []
