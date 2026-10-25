import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Listing, Reel
from app.db.session import get_db
from app.schemas.operations import ListingStatusIn, ModerationIn

router = APIRouter()


def require_key(value: str | None, expected: str, key_name: str) -> None:
    if value is None or not hmac.compare_digest(value, expected):
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": f"Invalid {key_name}"},
        )


@router.post("/internal/listings/{listing_id}/status")
async def update_listing_status(
    listing_id: UUID,
    data: ListingStatusIn,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    require_key(x_internal_key, settings.INTERNAL_API_KEY, "internal key")
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Listing not found"})
    listing.status = data.status
    await session.commit()
    return {"status": listing.status}


@router.post("/admin/reels/{reel_id}/moderation")
async def moderate_reel(
    reel_id: UUID,
    data: ModerationIn,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    require_key(x_admin_key, settings.ADMIN_API_KEY, "admin key")
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.status != "moderation":
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Reel is not awaiting moderation"})
    if data.decision == "approve":
        reel.status = "published"
        reel.published_at = datetime.now(timezone.utc)
        reel.reject_reason = None
    else:
        reel.status = "rejected"
        reel.reject_reason = data.reason or "Rejected by moderator"
    await session.commit()
    return {"status": reel.status}
