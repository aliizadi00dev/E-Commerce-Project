from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    order_id: int
    method: str
    gateway: str | None = None
    gateway_reference: str | None = None
    status: str = "pending"
    amount: Decimal


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    method: str | None = None
    gateway: str | None = None
    gateway_reference: str | None = None
    status: str | None = None
    paid_at: datetime | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid_at: datetime | None = None
    created_at: datetime
