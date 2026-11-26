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


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    method: PaymentMethod | None = None
    gateway: str | None = None
    gateway_reference: str | None = None
    status: PaymentStatus | None = None
    paid_at: datetime | None = None


class PaymentRead(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paid_at: datetime | None = None
    created_at: datetime
