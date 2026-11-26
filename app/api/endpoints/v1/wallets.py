from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, is_admin, require_self_or_admin
from app.database import get_db
from app.models.users import User
from app.models.wallets import Wallet, WalletTransaction
from app.schemas.wallets import WalletCreate, WalletRead, WalletTransactionCreate, WalletTransactionRead

router = APIRouter(tags=["Wallets"])


async def _get_wallet_or_404(wallet_id: int, db: AsyncSession) -> Wallet:
    result = await db.execute(
        select(Wallet).options(selectinload(Wallet.transactions)).where(Wallet.id == wallet_id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


def _require_wallet_owner(wallet: Wallet, current_user: User) -> None:
    require_self_or_admin(current_user, wallet.user_id, "You can only access your own wallet")


@router.post("/", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: WalletCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet already exists for this user")

    wallet = Wallet(user_id=current_user.id, **payload.model_dump())
    db.add(wallet)
    await db.commit()
    return await _get_wallet_or_404(wallet.id, db)


@router.get("/", response_model=list[WalletRead])
async def list_wallets(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    statement = select(Wallet).options(selectinload(Wallet.transactions))
    if not is_admin(current_user):
        statement = statement.where(Wallet.user_id == current_user.id)
    result = await db.execute(statement.order_by(Wallet.id))
    return result.scalars().all()


@router.get("/{wallet_id}", response_model=WalletRead)
async def get_wallet(
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = await _get_wallet_or_404(wallet_id, db)
    _require_wallet_owner(wallet, current_user)
    return wallet


@router.post("/{wallet_id}/transactions", response_model=WalletTransactionRead, status_code=status.HTTP_201_CREATED)
async def create_wallet_transaction(
    wallet_id: int,
    payload: WalletTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    wallet = await _get_wallet_or_404(wallet_id, db)

    tx = WalletTransaction(wallet_id=wallet_id, **payload.model_dump())
    if tx.type == "credit":
        wallet.balance = wallet.balance + tx.amount
    elif tx.type == "debit":
        if wallet.balance < tx.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance")
        wallet.balance = wallet.balance - tx.amount

    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


@router.get("/{wallet_id}/transactions", response_model=list[WalletTransactionRead])
async def list_wallet_transactions(
    wallet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    wallet = await _get_wallet_or_404(wallet_id, db)
    _require_wallet_owner(wallet, current_user)

    result = await db.execute(
        select(WalletTransaction).where(WalletTransaction.wallet_id == wallet_id).order_by(WalletTransaction.id)
    )
    return result.scalars().all()
