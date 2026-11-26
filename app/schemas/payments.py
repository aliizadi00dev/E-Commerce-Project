from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PaymentMethod, PaymentStatus


class PaymentBase(BaseModel):
    order_id: int
    method: PaymentMethod
    gateway: str | None = None
    gateway_reference: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Decimal = Field(gt=0)


class PaymentCreate(BaseModel):
    order_id: int
    method: PaymentMethod
    gateway: str | None = None
    gateway_reference: str | None = None


class PaymentUpdate(BaseModel):
    gateway: str | None = None
    gateway_reference: str | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid_at: datetime | None = None
    created_at: datetime
