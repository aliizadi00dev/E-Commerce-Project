from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, require_self_or_admin
from app.database import get_db
from app.models.categories import Category
from app.models.products import Product, ProductImage
from app.models.stores import Store
from app.models.users import User
from app.schemas.products import ProductCreate, ProductImageCreate, ProductImageRead, ProductRead, ProductUpdate

router = APIRouter(tags=["Products"])


async def _get_product_or_404(product_id: int, db: AsyncSession) -> Product:
    result = await db.execute(
        select(Product).options(selectinload(Product.images)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


async def _require_store_owner(store_id: int, db: AsyncSession, current_user: User) -> Store:
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    require_self_or_admin(current_user, store.owner_id, "You can only manage products in your own store")
    return store


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _require_store_owner(payload.store_id, db, current_user)
    if not await db.get(Category, payload.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    return await _get_product_or_404(product.id, db)


@router.get("/", response_model=list[ProductRead])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).options(selectinload(Product.images)).order_by(Product.id))
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_product_or_404(product_id, db)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product_or_404(product_id, db)
    await _require_store_owner(product.store_id, db, current_user)

    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and not await db.get(Category, data["category_id"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    return await _get_product_or_404(product_id, db)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product_or_404(product_id, db)
    await _require_store_owner(product.store_id, db, current_user)

    await db.delete(product)
    await db.commit()


@router.post("/{product_id}/images", response_model=ProductImageRead, status_code=status.HTTP_201_CREATED)
async def add_product_image(
    product_id: int,
    payload: ProductImageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product_or_404(product_id, db)
    await _require_store_owner(product.store_id, db, current_user)

    data = payload.model_dump()
    data["image_url"] = str(data["image_url"])
    image = ProductImage(product_id=product_id, **data)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


@router.get("/{product_id}/images", response_model=list[ProductImageRead])
async def list_product_images(product_id: int, db: AsyncSession = Depends(get_db)):
    await _get_product_or_404(product_id, db)
    result = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.position)
    )
    return result.scalars().all()
