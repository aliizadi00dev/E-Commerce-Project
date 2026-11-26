from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderStatus, StoreOrderStatus, sql_values
from app.database import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_orders_total_amount_nonnegative"),
        CheckConstraint(f"status IN ({sql_values(OrderStatus)})", name="ck_orders_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    address_id: Mapped[int] = mapped_column(ForeignKey("addresses.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(50), default=OrderStatus.PENDING, server_default="pending")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    address: Mapped["Address"] = relationship(back_populates="orders")
    store_orders: Mapped[list["StoreOrder"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(back_populates="order")


class StoreOrder(Base):
    __tablename__ = "store_orders"
    __table_args__ = (
        UniqueConstraint("order_id", "store_id", name="uq_store_orders_order_store"),
        CheckConstraint("subtotal >= 0", name="ck_store_orders_subtotal_nonnegative"),
        CheckConstraint(f"status IN ({sql_values(StoreOrderStatus)})", name="ck_store_orders_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(50), default=StoreOrderStatus.PENDING, server_default="pending")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="store_orders")
    store: Mapped["Store"] = relationship(back_populates="store_orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="store_order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_order_id: Mapped[int] = mapped_column(ForeignKey("store_orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    store_order: Mapped["StoreOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
