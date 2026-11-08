from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Listing, ListingImage, Promotion, Reel, ReelMedia, Swipe, User, WishlistItem
from app.db.session import get_db
from app.schemas.feed import (
    FeedItem,
    FeedResponse,
    ListingPage,
    Media,
    MediaItem,
    Price,
    Seller,
    SwipeIn,
    SwipeOut,
)
from app.services.recommender import recommend
from app.services.s3_service import s3_service

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def get_user_from_header(
    authorization: str | None, session: AsyncSession
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Bearer token required"},
        )
    return await get_current_user(authorization, session)


async def build_feed_item(
    session: AsyncSession,
    reel: Reel,
    listing: Listing,
    seller: User,
    user_id: UUID | None,
    promoted_ids: set[UUID],
) -> FeedItem:
    media_result = await session.scalars(
        select(ReelMedia)
        .where(ReelMedia.reel_id == reel.id)
        .order_by(ReelMedia.position, ReelMedia.id)
    )
    media_items = []
    for item in media_result.all():
        media_items.append(
            MediaItem(
                url=await s3_service.get_file_url(item.url),
                poster=(
                    await s3_service.get_file_url(item.poster_url)
                    if item.poster_url
                    else None
                ),
                duration_sec=item.duration_sec,
                width=item.width,
                height=item.height,
            )
        )
    in_wishlist = False
    if user_id:
        in_wishlist = bool(
            await session.scalar(
                select(WishlistItem.id)
                .where(
                    WishlistItem.user_id == user_id,
                    WishlistItem.listing_id == listing.id,
                )
                .limit(1)
            )
        )
    return FeedItem(
        reel_id=reel.id,
        listing_id=listing.id,
        media=Media(type=reel.media_type, items=media_items),
        title=listing.title,
        price=Price(amount=listing.price_amount, currency=listing.currency)
        if reel.show_price
        else None,
        description=reel.description or listing.description or "",
        seller=Seller(
            id=str(seller.id),
            name=seller.name or "Продавец",
            avatar_url=seller.avatar_url,
            rating=4.8,
        ),
        is_promoted=reel.id in promoted_ids,
        in_wishlist=in_wishlist,
    )


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(10, ge=1, le=20),
    cursor: UUID | None = None,
    session_id: str | None = Query(default=None, max_length=100),
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> FeedResponse:
    user = await get_user_from_header(authorization, session)
    now = utc_now()

    swipe_rows = await session.execute(
        select(Swipe.reel_id, Swipe.action, Swipe.created_at, Swipe.id)
        .where(Swipe.user_id == user.id, Swipe.undone_at.is_(None))
        .order_by(Swipe.created_at, Swipe.id)
    )
    excluded: set[UUID] = set()
    for reel_id, action, created_at, _ in swipe_rows.all():
        if action in {"like", "dislike"}:
            excluded.add(reel_id)
        elif action == "skip":
            swipe_at = (
                created_at.replace(tzinfo=timezone.utc)
                if created_at.tzinfo is None
                else created_at
            )
            if swipe_at > now - timedelta(hours=24):
                excluded.add(reel_id)

    candidate_query = (
        select(Reel, Listing, User)
        .join(Listing, Listing.id == Reel.listing_id)
        .join(User, User.id == Reel.seller_id)
        .where(
            Reel.status == "published",
            Reel.enabled.is_(True),
            Reel.seller_id != user.id,
            Listing.status == "active",
        )
    )
    candidate_result = await session.execute(
        candidate_query.order_by(
            Reel.published_at.desc().nullslast(), Reel.id.desc()
        )
    )
    candidates = [
        row for row in candidate_result.all() if row[0].id not in excluded
    ]
    ranked_ids = await recommend(
        session, user.id, limit=len(candidates), exclude_ids=list(excluded)
    )
    rank = {reel_id: index for index, reel_id in enumerate(ranked_ids)}
    candidates.sort(key=lambda row: rank.get(row[0].id, len(rank)))

    promotion_rows = await session.scalars(
        select(Promotion.reel_id)
        .where(
            Promotion.status == "active",
            Promotion.starts_at <= now,
            Promotion.active_until > now,
        )
    )
    promoted_ids = set(promotion_rows.all())

    organic = [row for row in candidates if row[0].id not in promoted_ids]
    promoted = [row for row in candidates if row[0].id in promoted_ids]
    ordered = []
    while organic:
        ordered.extend(organic[:4])
        del organic[:4]
        if organic and promoted:
            ordered.append(promoted.pop(0))
    ordered.extend(promoted)

    if cursor is not None:
        cursor_index = next(
            (index for index, row in enumerate(ordered) if row[0].id == cursor),
            None,
        )
        if cursor_index is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "Feed cursor not found"},
            )
        ordered = ordered[cursor_index + 1 :]

    page_rows = ordered[:limit]
    items = [
        await build_feed_item(session, reel, listing, seller, user.id, promoted_ids)
        for reel, listing, seller in page_rows
    ]
    next_cursor = items[-1].reel_id if len(ordered) > limit and items else None
    return FeedResponse(
        items=items,
        next_cursor=str(next_cursor) if next_cursor else None,
        session_id=session_id or str(uuid4()),
    )


@router.post("/swipes", response_model=SwipeOut)
async def create_swipe(
    data: SwipeIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> SwipeOut:
    user = await get_user_from_header(authorization, session)
    existing = await session.scalar(
        select(Swipe).where(Swipe.client_id == data.client_id)
    )
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=409,
                detail={"code": "validation_error", "message": "client_id already used"},
            )
        wishlist_count = await session.scalar(
            select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
        )
        swipe_count = await session.scalar(
            select(func.count(Swipe.id)).where(
                Swipe.user_id == user.id, Swipe.undone_at.is_(None)
            )
        )
        is_wishlisted = await session.scalar(
            select(WishlistItem.id)
            .where(WishlistItem.user_id == user.id)
            .where(
                WishlistItem.listing_id
                == await session.scalar(
                    select(Reel.listing_id).where(Reel.id == existing.reel_id)
                )
            )
            .limit(1)
        )
        return SwipeOut(
            in_wishlist=bool(is_wishlisted),
            wishlist_count=wishlist_count or 0,
            swipes_total=swipe_count or 0,
        )

    reel = await session.get(Reel, data.reel_id)
    if not reel:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    listing = await session.get(Listing, reel.listing_id)
    if data.action == "like" and listing.status != "active":
        raise HTTPException(
            status_code=409,
            detail={"code": "listing_unavailable", "message": "Listing is no longer available"},
        )

    swipe = Swipe(
        user_id=user.id,
        reel_id=reel.id,
        action=data.action,
        client_id=data.client_id,
        session_id=data.session_id,
        dwell_ms=data.dwell_ms,
        position=data.position,
    )
    session.add(swipe)
    in_wishlist = False
    if data.action == "like":
        existing_item = await session.scalar(
            select(WishlistItem.id).where(
                WishlistItem.user_id == user.id,
                WishlistItem.listing_id == listing.id,
            )
        )
        if not existing_item:
            session.add(
                WishlistItem(
                    user_id=user.id, listing_id=listing.id, reel_id=reel.id
                )
            )
            in_wishlist = True
        else:
            in_wishlist = True
    await session.commit()
    wishlist_count = await session.scalar(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
    )
    swipe_count = await session.scalar(
        select(func.count(Swipe.id)).where(
            Swipe.user_id == user.id, Swipe.undone_at.is_(None)
        )
    )
    return SwipeOut(
        in_wishlist=in_wishlist,
        wishlist_count=wishlist_count or 0,
        swipes_total=swipe_count or 0,
    )


@router.post("/swipes/undo")
async def undo_swipe(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> FeedItem:
    user = await get_user_from_header(authorization, session)
    last_swipe = await session.scalar(
        select(Swipe)
        .where(Swipe.user_id == user.id, Swipe.undone_at.is_(None))
        .order_by(Swipe.created_at.desc(), Swipe.id.desc())
        .limit(1)
    )
    if last_swipe is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "No swipe to undo"})
    last_swipe.undone_at = utc_now()
    reel = await session.get(Reel, last_swipe.reel_id)
    listing = await session.get(Listing, reel.listing_id)
    if last_swipe.action == "like":
        await session.execute(
            delete(WishlistItem).where(
                WishlistItem.user_id == user.id,
                WishlistItem.listing_id == listing.id,
            )
        )
    seller = await session.get(User, reel.seller_id)
    promotion_ids = set(
        (await session.scalars(
            select(Promotion.reel_id).where(
                Promotion.status == "active",
                Promotion.active_until > utc_now(),
            )
        )).all()
    )
    await session.commit()
    return await build_feed_item(session, reel, listing, seller, user.id, promotion_ids)


async def get_feed_reel(
    reel_id: UUID,
    user_id: UUID | None,
    session: AsyncSession,
) -> FeedItem:
    row = (
        await session.execute(
            select(Reel, Listing, User)
            .join(Listing, Listing.id == Reel.listing_id)
            .join(User, User.id == Reel.seller_id)
            .where(Reel.id == reel_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    reel, listing, seller = row
    promotions = await session.scalars(
        select(Promotion.reel_id).where(
            Promotion.reel_id == reel.id,
            Promotion.status == "active",
            Promotion.active_until > utc_now(),
        )
    )
    return await build_feed_item(
        session, reel, listing, seller, user_id, set(promotions.all())
    )


@router.get("/reels/{reel_id}", response_model=FeedItem)
async def get_reel(
    reel_id: UUID,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> FeedItem:
    user = await get_user_from_header(authorization, session)
    return await get_feed_reel(reel_id, user.id, session)


@router.get("/listings/{listing_id}", response_model=ListingPage)
async def get_listing(
    listing_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> ListingPage:
    listing = await session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Listing not found"})
    seller = await session.get(User, listing.seller_id)
    image_rows = await session.scalars(
        select(ListingImage)
        .where(ListingImage.listing_id == listing.id)
        .order_by(ListingImage.position, ListingImage.id)
    )
    return ListingPage(
        listing_id=listing.id,
        title=listing.title,
        description=listing.description or "",
        price=Price(amount=listing.price_amount, currency=listing.currency),
        city=listing.city or "",
        seller=Seller(
            id=str(seller.id),
            name=seller.name or "Продавец",
            avatar_url=seller.avatar_url,
            rating=4.8,
        ),
        status={
            "active": "available",
            "sold": "sold",
            "removed": "removed",
        }[listing.status],
        listing_url=listing.listing_url or "",
        images=[MediaItem(url=image.url) for image in image_rows.all()],
    )
