from fastapi import FastAPI, APIRouter

from app.api.endpoints import products, users

app = FastAPI()

api_v1 = APIRouter(prefix="/api/v1")


api_v1.include_router(users.router, prefix="/users", tags=["Users"])
api_v1.include_router(products.router, prefix="/products", tags=["Products"])

app.include_router(api_v1)
