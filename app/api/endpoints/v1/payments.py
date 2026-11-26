from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, is_admin
from app.database import get_db
from app.models.orders import Order
from app.models.payments import Payment
from app.models.users import User
from app.schemas.payments import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(tags=["Payments"])


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
    order = await db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only pay for your own orders",
        )

    payment = Payment(**payload.model_dump())
    if payment.status == "paid" and payment.paid_at is None:
        payment.paid_at = datetime.now(timezone.utc)
    db.add(payment)
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
    payment = await _get_payment_or_404(payment_id, db)
    order = await db.get(Order, payment.order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.user_id != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update payments for your own orders",
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(payment, key, value)
    if payment.status == "paid" and payment.paid_at is None:
        payment.paid_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(payment)
    return payment
