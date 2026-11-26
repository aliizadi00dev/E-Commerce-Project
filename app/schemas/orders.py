from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_order_id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal


class StoreOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    store_id: int
    status: str
    subtotal: Decimal
    created_at: datetime
    items: list[OrderItemRead] = []


class OrderCreateItem(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    address_id: int
    items: list[OrderCreateItem]


class OrderUpdate(BaseModel):
    status: str | None = None


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    address_id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    store_orders: list[StoreOrderRead] = []
