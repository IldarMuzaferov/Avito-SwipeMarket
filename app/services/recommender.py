from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, Listing, Reel, Swipe, UserInterest


def score_swipe(action: str, dwell_ms: int | None = None) -> float:
    score = {"like": 1.0, "dislike": -1.0, "skip": -0.05}.get(action, 0.0)
    if dwell_ms is not None:
        if dwell_ms >= 3_000:
            score += 0.5
        elif dwell_ms < 300:
            score -= 0.3
    return score


async def recommend(
    session: AsyncSession,
    user_id: UUID | str,
    limit: int = 20,
    exclude_ids: list[UUID] | None = None,
) -> list[UUID]:
    """Return eligible reels ranked by interests and the user's recent signals."""
    user_uuid = UUID(str(user_id))
    exclusions = set(exclude_ids or [])
    interest_result = await session.scalars(
        select(UserInterest.category_id).where(UserInterest.user_id == user_uuid)
    )
    interests = set(interest_result.all())

    result = await session.execute(
        select(Reel, Listing)
        .join(Listing, Listing.id == Reel.listing_id)
        .where(
            Reel.status == "published",
            Reel.enabled.is_(True),
            Reel.seller_id != user_uuid,
            Listing.status == "active",
        )
    )
    candidates = result.all()
    swipe_result = await session.execute(
        select(Swipe.reel_id, Swipe.action, Swipe.dwell_ms)
        .where(Swipe.user_id == user_uuid)
    )
    scores: dict[UUID, float] = defaultdict(float)
    for reel_id, action, dwell_ms in swipe_result.all():
        scores[reel_id] += score_swipe(action, dwell_ms)

    event_result = await session.execute(
        select(Event.reel_id, Event.type, Event.value_ms)
        .where(Event.user_id == user_uuid)
    )
    event_weights = {
        "open_listing": 2.0,
        "expand_description": 0.5,
        "watch": 0.5,
        "view": 0.1,
        "sound_toggle": 0.0,
    }
    for reel_id, event_type, value_ms in event_result.all():
        scores[reel_id] += event_weights.get(event_type, 0.0)
        if event_type == "watch" and value_ms and value_ms >= 3_000:
            scores[reel_id] += 0.5

    category_by_reel = {reel.id: listing.category_id for reel, listing in candidates}
    ranked = [reel for reel, _ in candidates if reel.id not in exclusions]
    ranked.sort(
        key=lambda reel: (
            category_by_reel[reel.id] in interests,
            scores[reel.id],
            reel.published_at.timestamp() if reel.published_at else 0,
            str(reel.id),
        ),
        reverse=True,
    )
    return [reel.id for reel in ranked[:limit]]
