from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.carts import Cart, CartItem
from app.models.products import Product
from app.models.users import User
from app.schemas.carts import CartCreate, CartItemCreate, CartItemRead, CartItemUpdate, CartRead, CartUpdate

router = APIRouter()


@router.post("/", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def create_cart(payload: CartCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    cart = Cart(**payload.model_dump())
    db.add(cart)
    await db.commit()
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart.id))
    return result.scalar_one()


@router.get("/", response_model=list[CartRead])
async def list_carts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).order_by(Cart.id))
    return result.scalars().all()


@router.get("/{cart_id}", response_model=CartRead)
async def get_cart(cart_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id))
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


@router.patch("/{cart_id}", response_model=CartRead)
async def update_cart(cart_id: int, payload: CartUpdate, db: AsyncSession = Depends(get_db)):
    cart = await db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cart, key, value)
    await db.commit()
    result = await db.execute(select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id))
    return result.scalar_one()


@router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(cart_id: int, db: AsyncSession = Depends(get_db)):
    cart = await db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    await db.delete(cart)
    await db.commit()


@router.post("/{cart_id}/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
async def add_cart_item(cart_id: int, payload: CartItemCreate, db: AsyncSession = Depends(get_db)):
    cart = await db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    if not await db.get(Product, payload.product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    existing = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == payload.product_id)
    )
    item = existing.scalar_one_or_none()
    if item:
        item.quantity += payload.quantity
    else:
        item = CartItem(cart_id=cart_id, **payload.model_dump())
        db.add(item)

    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{cart_id}/items/{item_id}", response_model=CartItemRead)
async def update_cart_item(
    cart_id: int, item_id: int, payload: CartItemUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(CartItem, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    item.quantity = payload.quantity
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{cart_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(cart_id: int, item_id: int, db: AsyncSession = Depends(get_db)):
    item = await db.get(CartItem, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await db.delete(item)
    await db.commit()
