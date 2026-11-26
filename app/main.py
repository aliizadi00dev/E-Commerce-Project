from fastapi import APIRouter, FastAPI

import app.models  # noqa: F401
from app.api.endpoints.v1 import auth, carts, categories, orders, payments, products, stores, users, wallets


app = FastAPI(title="FastEcom", version="0.1.0")

api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth.router, prefix="/auth")
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
