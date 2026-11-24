from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orders import Order
from app.models.payments import Payment
from app.schemas.payments import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter()


@router.post("/", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(payload: PaymentCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(Order, payload.order_id):
        raise HTTPException(status_code=404, detail="Order not found")
    payment = Payment(**payload.model_dump())
    if payment.status == "paid" and payment.paid_at is None:
        payment.paid_at = datetime.now(timezone.utc)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/", response_model=list[PaymentRead])
async def list_payments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Payment).order_by(Payment.id))
    return result.scalars().all()


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
async def update_payment(payment_id: int, payload: PaymentUpdate, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(payment, key, value)
    if payment.status == "paid" and payment.paid_at is None:
        payment.paid_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)
    return payment
