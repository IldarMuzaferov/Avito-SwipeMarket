from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event, Listing, Reel, Swipe, UserInterest

EVENT_WEIGHTS = {
    "open_listing": 2.0,
    "expand_description": 0.5,
    "watch": 0.5,
    "view": 0.1,
    "sound_toggle": 0.0,
}


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
    """Rank eligible reels by category affinity, then freshness, with diversity."""
    user_uuid = UUID(str(user_id))
    exclusions = {UUID(str(reel_id)) for reel_id in (exclude_ids or [])}
    interest_result = await session.scalars(
        select(UserInterest.category_id).where(UserInterest.user_id == user_uuid)
    )
    interests = set(interest_result.all())

    result = await session.execute(
        select(Reel, Listing.category_id)
        .join(Listing, Listing.id == Reel.listing_id)
        .where(
            Reel.status == "published",
            Reel.enabled.is_(True),
            Reel.seller_id != user_uuid,
            Listing.status == "active",
        )
    )
    candidates: list[tuple[Reel, UUID | None]] = [
        (reel, category_id)
        for reel, category_id in result.all()
        if reel.id not in exclusions
    ]

    category_scores: dict[UUID | None, float] = defaultdict(float)
    swipe_result = await session.execute(
        select(Listing.category_id, Swipe.action, Swipe.dwell_ms)
        .join(Reel, Reel.id == Swipe.reel_id)
        .join(Listing, Listing.id == Reel.listing_id)
        .where(Swipe.user_id == user_uuid, Swipe.undone_at.is_(None))
    )
    for category_id, action, dwell_ms in swipe_result.all():
        category_scores[category_id] += score_swipe(action, dwell_ms)

    event_result = await session.execute(
        select(Listing.category_id, Event.type, Event.value_ms)
        .join(Reel, Reel.id == Event.reel_id)
        .join(Listing, Listing.id == Reel.listing_id)
        .where(Event.user_id == user_uuid)
    )
    for category_id, event_type, value_ms in event_result.all():
        category_scores[category_id] += EVENT_WEIGHTS.get(event_type, 0.0)
        if event_type == "watch" and value_ms and value_ms >= 3_000:
            category_scores[category_id] += 0.5

    for category_id in interests:
        category_scores[category_id] += 1.0

    candidates.sort(
        key=lambda reel: (
            category_scores[reel[1]],
            reel[0].published_at.timestamp() if reel[0].published_at else 0,
            str(reel[0].id),
        ),
        reverse=True,
    )

    ranked: list[tuple[Reel, UUID | None]] = []
    while candidates:
        batch = candidates[:4]
        del candidates[:4]
        ranked.extend(batch)
        if not candidates:
            break

        primary_category = batch[0][1]
        diverse_index = next(
            (
                index
                for index, (_, category_id) in enumerate(candidates)
                if category_id != primary_category
            ),
            0,
        )
        ranked.append(candidates.pop(diverse_index))

    return [reel.id for reel, _ in ranked[:limit]]
