from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import OrderStatus, PaymentMethod, PaymentStatus, StoreOrderStatus, WalletTransactionType
from app.core.security import get_current_user, is_admin
from app.database import get_db
from app.models.orders import Order
from app.models.payments import Payment
from app.models.users import User
from app.models.wallets import Wallet, WalletTransaction
from app.schemas.payments import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(tags=["Payments"])


async def _get_order_with_store_orders(order_id: int, db: AsyncSession) -> Order:
    result = await db.execute(
        select(Order).options(selectinload(Order.store_orders)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


async def _get_payment_or_404(payment_id: int, db: AsyncSession) -> Payment:
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await _get_order_with_store_orders(payload.order_id, db)
    if order.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own orders",
        )
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is not pending")

    existing = await db.execute(
        select(Payment).where(Payment.order_id == order.id, Payment.status == PaymentStatus.PAID)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order is already paid")

    amount = order.total_amount
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order total must be greater than zero")

    payment = Payment(
        order_id=order.id,
        method=payload.method,
        gateway=payload.gateway,
        gateway_reference=payload.gateway_reference,
        status=PaymentStatus.PENDING,
        amount=amount,
    )

    wallet = None
    if payload.method == PaymentMethod.WALLET:
        wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == order.user_id))
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        if wallet.balance < amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance")
        wallet.balance -= amount

    payment.status = PaymentStatus.PAID
    # paid_at is a naive timestamp column; store UTC without tzinfo for asyncpg.
    payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
    order.status = OrderStatus.PAID
    for store_order in order.store_orders:
        store_order.status = StoreOrderStatus.PAID

    db.add(payment)
    await db.flush()

    if wallet is not None:
        db.add(
            WalletTransaction(
                wallet_id=wallet.id,
                payment_id=payment.id,
                order_id=order.id,
                type=WalletTransactionType.DEBIT,
                amount=amount,
                description=f"Payment for order {order.id}",
            )
        )

    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/", response_model=list[PaymentRead])
async def list_payments(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    statement = select(Payment)
    if not is_admin(current_user):
        statement = statement.join(Order).where(Order.user_id == current_user.id)
    result = await db.execute(statement.order_by(Payment.id))
    return result.scalars().all()


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = await _get_payment_or_404(payment_id, db)
    order = await db.get(Order, payment.order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access payments for your own orders",
        )
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    payment = await _get_payment_or_404(payment_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, key, value)

    await db.commit()
    await db.refresh(payment)
    return payment
