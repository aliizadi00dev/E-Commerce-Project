from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.categories import Category
from app.models.products import Product, ProductImage
from app.models.stores import Store
from app.schemas.products import ProductCreate, ProductImageCreate, ProductImageRead, ProductRead, ProductUpdate

router = APIRouter()


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(Store, payload.store_id):
        raise HTTPException(status_code=404, detail="Store not found")
    if not await db.get(Category, payload.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    result = await db.execute(
        select(Product).options(selectinload(Product.images)).where(Product.id == product.id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[ProductRead])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).options(selectinload(Product.images)).order_by(Product.id))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).options(selectinload(Product.images)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, payload: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and not await db.get(Category, data["category_id"]):
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    result = await db.execute(
        select(Product).options(selectinload(Product.images)).where(Product.id == product_id)
    )
    return result.scalar_one()


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()


@router.post("/{product_id}/images", response_model=ProductImageRead, status_code=status.HTTP_201_CREATED)
async def add_product_image(product_id: int, payload: ProductImageCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    image = ProductImage(product_id=product_id, **payload.model_dump())
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


@router.get("/{product_id}/images", response_model=list[ProductImageRead])
async def list_product_images(product_id: int, db: AsyncSession = Depends(get_db)):
    if not await db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    result = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.position)
    )
    return result.scalars().all()
