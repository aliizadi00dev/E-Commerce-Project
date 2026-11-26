from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import StoreStatus, sql_values
from app.database import Base


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint(f"status IN ({sql_values(StoreStatus)})", name="ck_stores_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default=StoreStatus.ACTIVE, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="stores")
    products: Mapped[list["Product"]] = relationship(back_populates="store", cascade="all, delete-orphan")
    store_orders: Mapped[list["StoreOrder"]] = relationship(back_populates="store")
