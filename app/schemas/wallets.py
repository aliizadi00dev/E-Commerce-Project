from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WalletTransactionBase(BaseModel):
    type: str
    amount: Decimal
    description: str | None = None
    status: str = "completed"
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
    balance: Decimal = Decimal("0.00")


class WalletCreate(WalletBase):
    pass


class WalletUpdate(BaseModel):
    balance: Decimal | None = None


class WalletRead(WalletBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    updated_at: datetime
    transactions: list[WalletTransactionRead] = []
