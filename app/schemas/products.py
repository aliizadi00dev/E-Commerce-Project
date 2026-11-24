from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductImageBase(BaseModel):
    image_url: str
    alt_text: str | None = None
    position: int = 0


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageRead(ProductImageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int


class ProductBase(BaseModel):
    store_id: int
    category_id: int
    name: str
    description: str | None = None
    price: Decimal
    stock: int = 0
    status: str = "active"


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    stock: int | None = None
    status: str | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    images: list[ProductImageRead] = []
