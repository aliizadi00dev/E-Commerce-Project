from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stores import Store
from app.models.users import User
from app.schemas.stores import StoreCreate, StoreRead, StoreUpdate

router = APIRouter()


@router.post("/", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
async def create_store(payload: StoreCreate, db: AsyncSession = Depends(get_db)):
    owner = await db.get(User, payload.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    existing = await db.execute(select(Store).where(Store.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Store slug already exists")
    store = Store(**payload.model_dump())
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
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.patch("/{store_id}", response_model=StoreRead)
async def update_store(store_id: int, payload: StoreUpdate, db: AsyncSession = Depends(get_db)):
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(store, key, value)
    await db.commit()
    await db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(store_id: int, db: AsyncSession = Depends(get_db)):
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    await db.delete(store)
    await db.commit()
