from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, hash_password, is_admin, require_self_or_admin
from app.database import get_db
from app.models.orders import Order
from app.models.users import Address, User
from app.schemas.users import AddressCreate, AddressRead, AddressUpdate, UserCreate, UserRead, UserUpdate

router = APIRouter(tags=["Users"])


async def _get_user_or_404(user_id: int, db: AsyncSession) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _ensure_identity_available(db: AsyncSession, data: dict, user_id: int | None = None) -> None:
    if "email" not in data and "username" not in data:
        return

    conditions = []
    if "email" in data:
        conditions.append(User.email == data["email"])
    if "username" in data:
        conditions.append(User.username == data["username"])

    statement = select(User).where(or_(*conditions))
    if user_id is not None:
        statement = statement.where(User.id != user_id)

    result = await db.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email or username already exists",
        )


async def _update_user(user_id: int, payload: UserUpdate, db: AsyncSession) -> User:
    user = await _get_user_or_404(user_id, db)
    data = payload.model_dump(exclude_unset=True)
    await _ensure_identity_available(db, data, user_id)

    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))

    for key, value in data.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user


async def _delete_user(user_id: int, db: AsyncSession) -> None:
    user = await _get_user_or_404(user_id, db)

    orders = await db.execute(select(Order.id).where(Order.user_id == user_id).limit(1))
    if orders.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has orders and cannot be deleted",
        )

    await db.delete(user)
    await db.commit()


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump()
    await _ensure_identity_available(db, data)

    user = User(
        username=data["username"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        password_hash=hash_password(data["password"]),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_current_user(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _update_user(current_user.id, payload, db)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _delete_user(current_user.id, db)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only view your own account")
    return await _get_user_or_404(user_id, db)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only update your own account")
    return await _update_user(user_id, payload, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only delete your own account")
    await _delete_user(user_id, db)


@router.post("/{user_id}/addresses", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(
    user_id: int,
    payload: AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only manage your own addresses")
    await _get_user_or_404(user_id, db)

    address = Address(user_id=user_id, **payload.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address


@router.get("/{user_id}/addresses", response_model=list[AddressRead])
async def list_addresses(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only view your own addresses")
    await _get_user_or_404(user_id, db)

    result = await db.execute(select(Address).where(Address.user_id == user_id).order_by(Address.id))
    return result.scalars().all()


@router.patch("/{user_id}/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    user_id: int,
    address_id: int,
    payload: AddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only manage your own addresses")

    address = await db.get(Address, address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(address, key, value)
    await db.commit()
    await db.refresh(address)
    return address


@router.delete("/{user_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    user_id: int,
    address_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self_or_admin(current_user, user_id, "You can only manage your own addresses")

    address = await db.get(Address, address_id)
    if not address or address.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    await db.delete(address)
    await db.commit()
