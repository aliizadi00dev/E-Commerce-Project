from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.endpoints.v1.carts import get_active_cart
from app.core.enums import (
    CartStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    StoreOrderStatus,
    WalletTransactionType,
)
from app.core.security import get_current_user, is_admin, require_self_or_admin
from app.database import get_db
from app.models.orders import Order, OrderItem, StoreOrder
from app.models.payments import Payment
from app.models.products import Product
from app.models.users import Address, User
from app.models.wallets import Wallet, WalletTransaction
from app.schemas.orders import CheckoutRequest, OrderCreate, OrderRead, OrderUpdate

router = APIRouter(tags=["Orders"])


def _order_query():
    return select(Order).options(selectinload(Order.store_orders).selectinload(StoreOrder.items))


async def _get_order_or_404(order_id: int, db: AsyncSession) -> Order:
    result = await db.execute(_order_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def _require_order_owner(order: Order, current_user: User) -> None:
    require_self_or_admin(current_user, order.user_id, "You can only access your own orders")


async def _prepare_lines(db: AsyncSession, lines: list[tuple[int, int]]) -> dict[int, tuple[Product, int]]:
    if not lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

    aggregated: dict[int, int] = defaultdict(int)
    for product_id, quantity in lines:
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than zero",
            )
        aggregated[product_id] += quantity

    result = await db.execute(select(Product).where(Product.id.in_(list(aggregated))))
    products = {product.id: product for product in result.scalars().all()}

    missing = [product_id for product_id in aggregated if product_id not in products]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Products not found: {missing}")

    for product_id, quantity in aggregated.items():
        if products[product_id].stock < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product_id}",
            )

    return {product_id: (products[product_id], quantity) for product_id, quantity in aggregated.items()}


async def _create_order_from_lines(
    user_id: int,
    address_id: int,
    lines: list[tuple[int, int]],
    db: AsyncSession,
) -> Order:
    prepared = await _prepare_lines(db, lines)

    grouped: dict[int, list[tuple[Product, int]]] = defaultdict(list)
    for product, quantity in prepared.values():
        grouped[product.store_id].append((product, quantity))

    order = Order(user_id=user_id, address_id=address_id, status=OrderStatus.PENDING, total_amount=Decimal("0.00"))
    db.add(order)
    await db.flush()

    total_amount = Decimal("0.00")
    for store_id, store_items in grouped.items():
        subtotal = sum((product.price * quantity for product, quantity in store_items), Decimal("0.00"))
        store_order = StoreOrder(
            order_id=order.id,
            store_id=store_id,
            status=StoreOrderStatus.PENDING,
            subtotal=subtotal,
        )
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
    await db.flush()
    return order


async def _get_owned_address_or_404(address_id: int, user_id: int, db: AsyncSession) -> Address:
    address = await db.get(Address, address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found for this user")
    return address


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_address_or_404(payload.address_id, current_user.id, db)
    order = await _create_order_from_lines(
        current_user.id,
        payload.address_id,
        [(item.product_id, item.quantity) for item in payload.items],
        db,
    )
    await db.commit()
    return await _get_order_or_404(order.id, db)


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_address_or_404(payload.address_id, current_user.id, db)

    cart = await get_active_cart(current_user.id, db)
    if not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    order = await _create_order_from_lines(
        current_user.id,
        payload.address_id,
        [(item.product_id, item.quantity) for item in cart.items],
        db,
    )

    cart.items.clear()
    cart.status = CartStatus.CHECKED_OUT
    await db.commit()
    return await _get_order_or_404(order.id, db)


@router.get("/", response_model=list[OrderRead])
async def list_orders(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    statement = _order_query()
    if not is_admin(current_user):
        statement = statement.where(Order.user_id == current_user.id)
    result = await db.execute(statement.order_by(Order.id))
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await _get_order_or_404(order_id, db)
    _require_order_owner(order, current_user)
    return order


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    order = await _get_order_or_404(order_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    await db.commit()
    return await _get_order_or_404(order_id, db)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await _get_order_or_404(order_id, db)
    _require_order_owner(order, current_user)

    if order.status in {OrderStatus.CANCELLED, OrderStatus.SHIPPED, OrderStatus.DELIVERED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order cannot be cancelled")

    for store_order in order.store_orders:
        for item in store_order.items:
            product = await db.get(Product, item.product_id)
            if product:
                product.stock += item.quantity
        store_order.status = StoreOrderStatus.CANCELLED

    paid_result = await db.execute(
        select(Payment).where(Payment.order_id == order.id, Payment.status == PaymentStatus.PAID)
    )
    paid_payment = paid_result.scalar_one_or_none()
    if paid_payment:
        if paid_payment.method == PaymentMethod.WALLET:
            wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id))
            wallet = wallet_result.scalar_one_or_none()
            if wallet:
                wallet.balance += paid_payment.amount
                db.add(
                    WalletTransaction(
                        wallet_id=wallet.id,
                        payment_id=paid_payment.id,
                        order_id=order.id,
                        type=WalletTransactionType.CREDIT,
                        amount=paid_payment.amount,
                        description=f"Refund for order {order.id}",
                    )
                )
        paid_payment.status = PaymentStatus.REFUNDED

    order.status = OrderStatus.CANCELLED
    await db.commit()
    return await _get_order_or_404(order_id, db)
