from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.users import User
from app.models.wallets import Wallet, WalletTransaction
from app.schemas.wallets import WalletCreate, WalletRead, WalletTransactionCreate, WalletTransactionRead

router = APIRouter()


@router.post("/", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
async def create_wallet(payload: WalletCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    existing = await db.execute(select(Wallet).where(Wallet.user_id == payload.user_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Wallet already exists for this user")
    wallet = Wallet(**payload.model_dump())
    db.add(wallet)
    await db.commit()
    result = await db.execute(select(Wallet).options(selectinload(Wallet.transactions)).where(Wallet.id == wallet.id))
    return result.scalar_one()


@router.get("/", response_model=list[WalletRead])
async def list_wallets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).options(selectinload(Wallet.transactions)).order_by(Wallet.id))
    return result.scalars().all()


@router.get("/{wallet_id}", response_model=WalletRead)
async def get_wallet(wallet_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).options(selectinload(Wallet.transactions)).where(Wallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.post("/{wallet_id}/transactions", response_model=WalletTransactionRead, status_code=status.HTTP_201_CREATED)
async def create_wallet_transaction(
    wallet_id: int, payload: WalletTransactionCreate, db: AsyncSession = Depends(get_db)
):
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    tx = WalletTransaction(wallet_id=wallet_id, **payload.model_dump())
    if tx.type == "credit":
        wallet.balance = wallet.balance + tx.amount
    elif tx.type == "debit":
        if wallet.balance < tx.amount:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        wallet.balance = wallet.balance - tx.amount

    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.get("/{wallet_id}/transactions", response_model=list[WalletTransactionRead])
async def list_wallet_transactions(wallet_id: int, db: AsyncSession = Depends(get_db)):
    wallet = await db.get(Wallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    result = await db.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet_id).order_by(WalletTransaction.id)
    )
    return result.scalars().all()
