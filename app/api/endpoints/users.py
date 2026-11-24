import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.users import Address, User
from app.schemas.users import AddressCreate, AddressRead, AddressUpdate, UserCreate, UserRead, UserUpdate

router = APIRouter()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email or username already exists")

    user = User(
        username=payload.username,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))
    for key, value in data.items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/addresses", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(user_id: int, payload: AddressCreate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    address = Address(user_id=user_id, **payload.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


@router.get("/{user_id}/addresses", response_model=list[AddressRead])
async def list_addresses(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(select(Address).where(Address.user_id == user_id).order_by(Address.id))
    return result.scalars().all()


@router.patch("/{user_id}/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    user_id: int, address_id: int, payload: AddressUpdate, db: AsyncSession = Depends(get_db)
):
    address = await db.get(Address, address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=404, detail="Address not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(address, key, value)
    await db.commit()
    await db.refresh(address)
    return address


@router.delete("/{user_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(user_id: int, address_id: int, db: AsyncSession = Depends(get_db)):
    address = await db.get(Address, address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.delete(address)
    await db.commit()
