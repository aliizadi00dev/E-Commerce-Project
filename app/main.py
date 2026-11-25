from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

import app.models  # noqa: F401
from app.api.endpoints.v1 import carts, categories, orders, payments, products, stores, users, wallets
from app.database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="FastEcom", version="0.1.0", lifespan=lifespan)

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(users.router, prefix="/users", tags=["Users"])
api_v1.include_router(stores.router, prefix="/stores", tags=["Stores"])
api_v1.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_v1.include_router(products.router, prefix="/products", tags=["Products"])
api_v1.include_router(carts.router, prefix="/carts", tags=["Carts"])
api_v1.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_v1.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_v1.include_router(wallets.router, prefix="/wallets", tags=["Wallets"])

app.include_router(api_v1)


@app.get("/health")
async def health():
    return {"status": "ok"}
