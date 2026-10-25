from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.feed import router as feed_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api/v1")
api_router.include_router(feed_router, prefix="/api/v1")

@api_router.get("/health")
async def health():
    return {"status": "ok"}