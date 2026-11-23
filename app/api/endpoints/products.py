from fastapi import APIRouter


router = APIRouter()


@router.get("/")
async def get_products():
    return "Products"


@router.get("/{vendor}/{product_id}")
async def get_product(vendor: str, product_id: int):
    print("helskdljflskd")
    return {vendor: product_id}
