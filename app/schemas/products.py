from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.core.enums import ProductStatus


class ProductImageBase(BaseModel):
    image_url: HttpUrl
    alt_text: str | None = None
    position: int = Field(default=0, ge=0)


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
    price: Decimal = Field(ge=0)
    stock: int = Field(default=0, ge=0)
    status: ProductStatus = ProductStatus.ACTIVE


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    status: ProductStatus | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    images: list[ProductImageRead] = []
