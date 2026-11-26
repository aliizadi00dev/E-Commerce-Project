from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import OrderStatus, StoreOrderStatus


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_order_id: int
    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class StoreOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    store_id: int
    status: StoreOrderStatus
    subtotal: Decimal
    created_at: datetime
    items: list[OrderItemRead] = []


class OrderCreateItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    address_id: int
    items: list[OrderCreateItem]


class CheckoutRequest(BaseModel):
    address_id: int


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    address_id: int
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    store_orders: list[StoreOrderRead] = []
