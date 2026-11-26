from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WalletTransactionStatus, WalletTransactionType, sql_values
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_wallets_balance_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="wallet")
    transactions: Mapped[list["WalletTransaction"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_wallet_transactions_amount_positive"),
        CheckConstraint(f"type IN ({sql_values(WalletTransactionType)})", name="ck_wallet_transactions_type"),
        CheckConstraint(f"status IN ({sql_values(WalletTransactionStatus)})", name="ck_wallet_transactions_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default=WalletTransactionStatus.COMPLETED, server_default="completed")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
    payment: Mapped["Payment | None"] = relationship(back_populates="wallet_transactions")
    order: Mapped["Order | None"] = relationship(back_populates="wallet_transactions")
