from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.session import get_db
from app.schemas.feed import FeedResponse, FeedItem, SwipeIn, SwipeOut, ListingPage, Media, MediaItem, Price, Seller
from app.db.models import Reel, ReelMedia, Listing, User, Swipe, WishlistItem, Promotion, UserInterest
from app.core.security import get_current_user
from app.services.recommender import recommend, score_swipe
from uuid import UUID, uuid4
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(10, ge=1, le=20),
    cursor: str | None = None,
    session_id: str | None = None,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)
    session_id = session_id or str(uuid4())

    # Действия пользователя, чтобы не показывать лайкнутые/дизлайкнутые
    swipes_res = await session.execute(
        select(Swipe.reel_id, Swipe.action, Swipe.created_at)
        .where(Swipe.user_id == user.id)
    )
    swipes = swipes_res.all()

    exclude_ids = []
    now = datetime.utcnow()
    for reel_id, action, created_at in swipes:
        if action in ("like", "dislike"):
            exclude_ids.append(reel_id)
        elif action == "skip":
            # Пропущенные скрываем на 24 часа
            if now - created_at < timedelta(hours=24):
                exclude_ids.append(reel_id)

    # Кол-во свайпов
    swipes_count = len([s for s in swipes if s[1] in ("like", "dislike")])

    # Выбираем рилсы
    if swipes_count < 5:
        # Холодный старт: по интересам или популярные
        interests_res = await session.execute(
            select(UserInterest.category_id).where(UserInterest.user_id == user.id)
        )
        cat_ids = [r[0] for r in interests_res.all()]

        query = select(Reel).join(Listing).where(
            Reel.status == "published",
            Reel.enabled == True,
            Reel.seller_id != user.id,
            Listing.status == "active"
        )
        if cat_ids:
            query = query.where(Listing.category_id.in_(cat_ids))

        query = query.order_by(Reel.published_at.desc()).limit(limit * 2)
        res = await session.execute(query)
        reels = res.scalars().all()
        reels = [r for r in reels if r.id not in exclude_ids][:limit]
    else:
        # После 5 свайпов через рекомендации
        rec_ids = await recommend(session, str(user.id), limit, exclude_ids)
        if rec_ids:
            res = await session.execute(select(Reel).where(Reel.id.in_(rec_ids)))
            reels = res.scalars().all()
        else:
            reels = []

    # Продвигаемые рилсы (максимум 1 на каждые 5 карточек)
    promotions_res = await session.execute(
        select(Promotion.reel_id).where(
            Promotion.status == "active",
            Promotion.active_until > now
        )
    )
    promoted_reel_ids = set(r[0] for r in promotions_res.all())

    # Формируем результат
    items = []
    for reel in reels:
        # Модель товара и продавца
        listing = await session.get(Listing, reel.listing_id)
        seller = await session.get(User, reel.seller_id)
        media_res = await session.execute(
            select(ReelMedia).where(ReelMedia.reel_id == reel.id).order_by(ReelMedia.position)
        )
        media_items = media_res.scalars().all()

        # Вишлист?
        wish_res = await session.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user.id,
                WishlistItem.listing_id == listing.id
            )
        )
        in_wishlist = wish_res.scalar_one_or_none() is not None

        items.append(FeedItem(
            reel_id=str(reel.id),
            listing_id=str(listing.id),
            media=Media(
                type=reel.media_type,
                items=[
                    MediaItem(
                        url=m.url,
                        poster=m.poster_url,
                        duration_sec=m.duration_sec,
                        width=m.width,
                        height=m.height
                    ) for m in media_items
                ]
            ),
            title=listing.title,
            price=Price(amount=listing.price_amount, currency=listing.currency) if reel.show_price else None,
            description=reel.description or listing.description or "",
            seller=Seller(
                id=str(seller.id),
                name=seller.name or "Продавец",
                avatar_url=seller.avatar_url,
                rating=4.8
            ),
            is_promoted=reel.id in promoted_reel_ids,
            in_wishlist=in_wishlist
        ))

    next_cursor = str(items[-1].reel_id) if len(items) == limit else None

    return FeedResponse(
        items=items,
        next_cursor=next_cursor,
        session_id=session_id
    )

@router.post("/swipes", response_model=SwipeOut)
async def create_swipe(
    data: SwipeIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    # Идемпотентность по client_id
    existing = await session.execute(
        select(Swipe).where(Swipe.client_id == UUID(data.client_id))
    )
    if existing.scalar_one_or_none():
        # Повтор — вернём текущий статус
        wish_count = await session.execute(
            select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
        )
        swipes_count = await session.execute(
            select(func.count(Swipe.id)).where(Swipe.user_id == user.id)
        )
        return SwipeOut(
            in_wishlist=False,
            wishlist_count=wish_count.scalar_one(),
            swipes_total=swipes_count.scalar_one()
        )

    reel = await session.get(Reel, UUID(data.reel_id))
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    listing = await session.get(Listing, reel.listing_id)
    if listing.status != "active" and data.action == "like":
        raise HTTPException(status_code=409, detail="Listing unavailable")

    # Сохраняем свайп
    swipe = Swipe(
        id=uuid4(),
        user_id=user.id,
        reel_id=reel.id,
        action=data.action,
        client_id=UUID(data.client_id),
        session_id=data.session_id,
        dwell_ms=data.dwell_ms,
        position=data.position
    )
    session.add(swipe)

    in_wishlist = False
    if data.action == "like":
        # Добавляем в вишлист
        wish_existing = await session.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user.id,
                WishlistItem.listing_id == listing.id
            )
        )
        if not wish_existing.scalar_one_or_none():
            wish_item = WishlistItem(
                id=uuid4(),
                user_id=user.id,
                listing_id=listing.id,
                reel_id=reel.id
            )
            session.add(wish_item)
            in_wishlist = True

    await session.commit()

    # Считаем количество
    wish_count = await session.execute(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
    )
    swipes_count = await session.execute(
        select(func.count(Swipe.id)).where(Swipe.user_id == user.id)
    )

    return SwipeOut(
        in_wishlist=in_wishlist,
        wishlist_count=wish_count.scalar_one(),
        swipes_total=swipes_count.scalar_one()
    )

@router.get("/listings/{listing_id}", response_model=ListingPage)
async def get_listing(listing_id: str, session: AsyncSession = Depends(get_db)):
    listing = await session.get(Listing, UUID(listing_id))
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    seller = await session.get(User, listing.seller_id)

    return ListingPage(
        listing_id=str(listing.id),
        title=listing.title,
        description=listing.description or "",
        price=Price(amount=listing.price_amount, currency=listing.currency),
        city=listing.city or "Москва",
        seller=Seller(
            id=str(seller.id),
            name=seller.name or "Продавец",
            avatar_url=seller.avatar_url,
            rating=4.8
        ),
        status="available" if listing.status == "active" else "sold",
        listing_url=listing.listing_url or f"https://avito.ru/item/{listing.id}",
        images=[MediaItem(url=f"https://cdn.example.com/listings/{listing.id}/1.jpg")]
    )