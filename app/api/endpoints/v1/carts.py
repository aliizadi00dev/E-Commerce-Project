from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, is_admin, require_self_or_admin
from app.database import get_db
from app.models.carts import Cart, CartItem
from app.models.products import Product
from app.models.users import User
from app.schemas.carts import CartCreate, CartItemCreate, CartItemRead, CartItemUpdate, CartRead, CartUpdate

router = APIRouter(tags=["Carts"])


def _attach_total(cart: Cart) -> Cart:
    cart.total_amount = sum((item.product.price * item.quantity for item in cart.items), Decimal("0.00"))
    return cart


async def _get_cart_or_404(cart_id: int, db: AsyncSession) -> Cart:
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.id == cart_id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return _attach_total(cart)


async def get_active_cart(user_id: int, db: AsyncSession) -> Cart:
    result = await db.execute(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.product))
        .where(Cart.user_id == user_id, Cart.status == "active")
        .order_by(Cart.id.desc())
        .limit(1)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active cart not found")
    return _attach_total(cart)


def _require_cart_owner(cart: Cart, current_user: User) -> None:
    require_self_or_admin(current_user, cart.user_id, "You can only access your own cart")


@router.post("/", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def create_cart(
    payload: CartCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = Cart(user_id=current_user.id, **payload.model_dump())
    db.add(cart)
    await db.commit()
    return await _get_cart_or_404(cart.id, db)


@router.get("/mine", response_model=CartRead)
async def get_my_cart(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await get_active_cart(current_user.id, db)


@router.get("/", response_model=list[CartRead])
async def list_carts(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    statement = select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product))
    if not is_admin(current_user):
        statement = statement.where(Cart.user_id == current_user.id)
    result = await db.execute(statement.order_by(Cart.id))
    return [_attach_total(cart) for cart in result.scalars().all()]


@router.get("/{cart_id}", response_model=CartRead)
async def get_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)
    return cart


@router.patch("/{cart_id}", response_model=CartRead)
async def update_cart(
    cart_id: int,
    payload: CartUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cart, key, value)
    await db.commit()
    return await _get_cart_or_404(cart_id, db)


@router.delete("/{cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)

    await db.delete(cart)
    await db.commit()


@router.post("/{cart_id}/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
async def add_cart_item(
    cart_id: int,
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)

    product = await db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == payload.product_id)
    )
    item = existing.scalar_one_or_none()
    requested_quantity = item.quantity + payload.quantity if item else payload.quantity
    if product.stock < requested_quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    if item:
        item.quantity = requested_quantity
    else:
        item = CartItem(cart_id=cart_id, **payload.model_dump())
        db.add(item)

    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{cart_id}/items/{item_id}", response_model=CartItemRead)
async def update_cart_item(
    cart_id: int,
    item_id: int,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)

    item = await db.get(CartItem, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    product = await db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.stock < payload.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    item.quantity = payload.quantity
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{cart_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    cart_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = await _get_cart_or_404(cart_id, db)
    _require_cart_owner(cart, current_user)

    item = await db.get(CartItem, item_id)
    if not item or item.cart_id != cart_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    await db.delete(item)
    await db.commit()
