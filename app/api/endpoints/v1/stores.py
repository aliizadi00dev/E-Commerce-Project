from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_self_or_admin
from app.database import get_db
from app.models.stores import Store
from app.models.users import User
from app.schemas.stores import StoreCreate, StoreRead, StoreUpdate

router = APIRouter(tags=["Stores"])


async def _get_store_or_404(store_id: int, db: AsyncSession) -> Store:
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    return store


async def _ensure_slug_available(db: AsyncSession, slug: str, store_id: int | None = None) -> None:
    statement = select(Store).where(Store.slug == slug)
    if store_id is not None:
        statement = statement.where(Store.id != store_id)

    result = await db.execute(statement)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Store slug already exists")


@router.post("/", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
async def create_store(
    payload: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _ensure_slug_available(db, payload.slug)
    store = Store(owner_id=current_user.id, **payload.model_dump())
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store


@router.get("/", response_model=list[StoreRead])
async def list_stores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Store).order_by(Store.id))
    return result.scalars().all()


@router.get("/{store_id}", response_model=StoreRead)
async def get_store(store_id: int, db: AsyncSession = Depends(get_db)):
    return await _get_store_or_404(store_id, db)


@router.patch("/{store_id}", response_model=StoreRead)
async def update_store(
    store_id: int,
    payload: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await _get_store_or_404(store_id, db)
    require_self_or_admin(current_user, store.owner_id, "You can only update your own store")

    data = payload.model_dump(exclude_unset=True)
    if "slug" in data:
        await _ensure_slug_available(db, data["slug"], store_id)

    for key, value in data.items():
        setattr(store, key, value)
    await db.commit()
    await db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await _get_store_or_404(store_id, db)
    require_self_or_admin(current_user, store.owner_id, "You can only delete your own store")

    await db.delete(store)
    await db.commit()
