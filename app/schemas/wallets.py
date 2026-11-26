from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import WalletTransactionStatus, WalletTransactionType


class WalletTransactionBase(BaseModel):
    type: WalletTransactionType
    amount: Decimal = Field(gt=0)
    description: str | None = None
    status: WalletTransactionStatus = WalletTransactionStatus.COMPLETED
    payment_id: int | None = None
    order_id: int | None = None


class WalletTransactionCreate(WalletTransactionBase):
    pass


class WalletTransactionRead(WalletTransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_id: int
    created_at: datetime


class WalletBase(BaseModel):
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)


class WalletCreate(WalletBase):
    pass


class WalletUpdate(BaseModel):
    balance: Decimal | None = Field(default=None, ge=0)


class WalletRead(WalletBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    updated_at: datetime
    transactions: list[WalletTransactionRead] = []
