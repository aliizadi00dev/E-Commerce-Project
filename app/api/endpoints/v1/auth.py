from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user, hash_password, is_legacy_password_hash, verify_password
from app.database import get_db
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.users import UserRead

router = APIRouter(tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if is_legacy_password_hash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        await db.commit()

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
