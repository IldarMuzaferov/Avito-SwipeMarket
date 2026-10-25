from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.feed import router as feed_router
from app.api.v1.wishlist import router as wishlist_router
from app.api.v1.seller import router as seller_router
from app.api.v1.promotion import router as promotion_router
from app.api.v1.operations import router as operations_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(feed_router, prefix="/api/v1")
api_router.include_router(wishlist_router, prefix="/api/v1")
api_router.include_router(seller_router, prefix="/api/v1")
api_router.include_router(promotion_router, prefix="/api/v1")
api_router.include_router(operations_router, prefix="/api/v1")

@api_router.get("/health")
@api_router.get("/api/v1/health", include_in_schema=False)
async def health():
    return {"status": "ok"}