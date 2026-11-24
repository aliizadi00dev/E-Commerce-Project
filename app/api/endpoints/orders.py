from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.orders import Order, OrderItem, StoreOrder
from app.models.products import Product
from app.models.users import Address, User
from app.schemas.orders import OrderCreate, OrderRead, OrderUpdate

router = APIRouter()


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    address = await db.get(Address, payload.address_id)
    if not address or address.user_id != payload.user_id:
        raise HTTPException(status_code=404, detail="Address not found for this user")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    product_ids = [item.product_id for item in payload.items]
    result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
    products = {product.id: product for product in result.scalars().all()}

    missing = [pid for pid in product_ids if pid not in products]
    if missing:
        raise HTTPException(status_code=404, detail=f"Products not found: {missing}")

    grouped: dict[int, list[tuple[Product, int]]] = {}
    for item in payload.items:
        product = products[item.product_id]
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for product {product.id}")
        grouped.setdefault(product.store_id, []).append((product, item.quantity))

    total_amount = Decimal("0.00")
    order = Order(user_id=payload.user_id, address_id=payload.address_id, status="pending", total_amount=total_amount)
    db.add(order)
    await db.flush()

    for store_id, store_items in grouped.items():
        subtotal = sum((product.price * quantity for product, quantity in store_items), Decimal("0.00"))
        store_order = StoreOrder(order_id=order.id, store_id=store_id, status="pending", subtotal=subtotal)
        db.add(store_order)
        await db.flush()

        for product, quantity in store_items:
            db.add(
                OrderItem(
                    store_order_id=store_order.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price=product.price,
                )
            )
            product.stock -= quantity
        total_amount += subtotal

    order.total_amount = total_amount
    await db.commit()

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.store_orders).selectinload(StoreOrder.items))
        .where(Order.id == order.id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[OrderRead])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).options(selectinload(Order.store_orders).selectinload(StoreOrder.items)).order_by(Order.id)
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.store_orders).selectinload(StoreOrder.items))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(order_id: int, payload: OrderUpdate, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    await db.commit()
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.store_orders).selectinload(StoreOrder.items))
        .where(Order.id == order_id)
    )
    return result.scalar_one()
