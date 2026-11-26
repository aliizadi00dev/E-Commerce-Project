from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ProductStatus, sql_values
from app.database import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        CheckConstraint(f"status IN ({sql_values(ProductStatus)})", name="ck_products_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(50), default=ProductStatus.ACTIVE, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    store: Mapped["Store"] = relationship(back_populates="products")
    category: Mapped["Category"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="product")


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_product_images_position_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    image_url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    product: Mapped["Product"] = relationship(back_populates="images")
