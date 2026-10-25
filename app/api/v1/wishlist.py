import secrets
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.db.session import get_db
from app.schemas.wishlist import (
    WishlistResponse, WishlistItemOut, WishlistShareOut, WishlistPrice,
    AddWishlistItemIn, ShareToggleIn, PublicWishlistResponse, PublicWishlistOwner,
    PublicWishlistItemOut
)
from app.db.models import WishlistItem, WishlistShare, Listing, Reel, User, ReelMedia
from app.core.security import get_current_user
from uuid import UUID, uuid4
from datetime import datetime

router = APIRouter()

def generate_share_token() -> str:
    return secrets.token_urlsafe(6)[:8]

@router.get("/wishlist", response_model=WishlistResponse)
async def get_wishlist(
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    # Запрос на получение элементов
    query = (
        select(WishlistItem, Listing, Reel)
        .join(Listing, WishlistItem.listing_id == Listing.id)
        .outerjoin(Reel, WishlistItem.reel_id == Reel.id)
        .where(WishlistItem.user_id == user.id)
        .order_by(WishlistItem.added_at.desc())
    )

    res = await session.execute(query)
    rows = res.all()

    # Считаем общее кол-во
    count_res = await session.execute(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
    )
    total_count = count_res.scalar_one()

    # Ссылка для шаринга
    share_res = await session.execute(
        select(WishlistShare).where(WishlistShare.user_id == user.id)
    )
    share = share_res.scalar_one_or_none()
    share_out = WishlistShareOut(
        enabled=share.enabled if share else False,
        url=f"https://avito.ru/wishlist/{share.token}" if (share and share.enabled and share.token) else None
    )

    items = []
    for wish_item, listing, reel in rows[:limit]:
        status_str = "available"
        if listing.status == "sold":
            status_str = "sold"
        elif listing.status == "removed":
            status_str = "removed"

        cover_url = reel.cover_url if reel else None

        items.append(WishlistItemOut(
            listing_id=str(listing.id),
            reel_id=str(reel.id) if reel else None,
            title=listing.title,
            price=WishlistPrice(amount=listing.price_amount, currency=listing.currency),
            cover_url=cover_url,
            city=listing.city or "Москва",
            status=status_str,
            added_at=wish_item.added_at
        ))

    next_cursor = str(items[-1].listing_id) if len(items) == limit else None

    return WishlistResponse(
        count=total_count,
        items=items,
        share=share_out,
        next_cursor=next_cursor
    )

@router.post("/wishlist/items", status_code=201)
async def add_wishlist_item(
    data: AddWishlistItemIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    listing_uuid = UUID(data.listing_id)
    listing = await session.get(Listing, listing_uuid)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Проверяем, есть ли уже в вишлисте (защита от дублей)
    existing = await session.execute(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.listing_id == listing_uuid
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "ok", "message": "Already in wishlist"}

    # Находим связанный рилс если есть
    reel_res = await session.execute(
        select(Reel).where(Reel.listing_id == listing_uuid)
    )
    reel = reel_res.scalar_one_or_none()

    item = WishlistItem(
        id=uuid4(),
        user_id=user.id,
        listing_id=listing.id,
        reel_id=reel.id if reel else None
    )
    session.add(item)
    await session.commit()
    return {"status": "ok"}

@router.delete("/wishlist/items/{listing_id}", status_code=204)
async def remove_wishlist_item(
    listing_id: str,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    listing_uuid = UUID(listing_id)
    await session.execute(
        delete(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.listing_id == listing_uuid
        )
    )
    await session.commit()
    return None

@router.get("/wishlist/share", response_model=WishlistShareOut)
async def get_wishlist_share(
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    share_res = await session.execute(
        select(WishlistShare).where(WishlistShare.user_id == user.id)
    )
    share = share_res.scalar_one_or_none()

    if not share:
        return WishlistShareOut(enabled=False, url=None)

    url = f"https://avito.ru/wishlist/{share.token}" if (share.enabled and share.token) else None
    return WishlistShareOut(enabled=share.enabled, url=url)

@router.put("/wishlist/share", response_model=WishlistShareOut)
async def toggle_wishlist_share(
    data: ShareToggleIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    share_res = await session.execute(
        select(WishlistShare).where(WishlistShare.user_id == user.id)
    )
    share = share_res.scalar_one_or_none()

    if not share:
        token_str = generate_share_token()
        share = WishlistShare(
            user_id=user.id,
            token=token_str,
            enabled=data.enabled,
            rotated_at=datetime.utcnow()
        )
        session.add(share)
    else:
        if data.enabled and not share.token:
            share.token = generate_share_token()
            share.rotated_at = datetime.utcnow()
        share.enabled = data.enabled

    await session.commit()

    url = f"https://avito.ru/wishlist/{share.token}" if (share.enabled and share.token) else None
    return WishlistShareOut(enabled=share.enabled, url=url)

@router.post("/wishlist/share/rotate", response_model=WishlistShareOut)
async def rotate_wishlist_share(
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    share_res = await session.execute(
        select(WishlistShare).where(WishlistShare.user_id == user.id)
    )
    share = share_res.scalar_one_or_none()

    new_token = generate_share_token()
    if not share:
        share = WishlistShare(
            user_id=user.id,
            token=new_token,
            enabled=True,
            rotated_at=datetime.utcnow()
        )
        session.add(share)
    else:
        share.token = new_token
        share.enabled = True
        share.rotated_at = datetime.utcnow()

    await session.commit()
    url = f"https://avito.ru/wishlist/{share.token}"
    return WishlistShareOut(enabled=True, url=url)

@router.get("/public/wishlists/{share_token}", response_model=PublicWishlistResponse)
async def get_public_wishlist(
    share_token: str,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_db)
):
    share_res = await session.execute(
        select(WishlistShare).where(WishlistShare.token == share_token)
    )
    share = share_res.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Wishlist not found"}}
        )

    if not share.enabled:
        raise HTTPException(
            status_code=410,
            detail={"error": {"code": "wishlist_disabled", "message": "Wishlist access disabled"}}
        )

    owner = await session.get(User, share.user_id)

    query = (
        select(WishlistItem, Listing, Reel)
        .join(Listing, WishlistItem.listing_id == Listing.id)
        .outerjoin(Reel, WishlistItem.reel_id == Reel.id)
        .where(WishlistItem.user_id == share.user_id)
        .order_by(WishlistItem.added_at.desc())
    )

    res = await session.execute(query)
    rows = res.all()

    count_res = await session.execute(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == share.user_id)
    )
    total_count = count_res.scalar_one()

    items = []
    for wish_item, listing, reel in rows[:limit]:
        status_str = "available"
        if listing.status in ("sold", "removed"):
            status_str = "sold"  # Друг видит все проданное/снятое как sold ("Уже купили")

        cover_url = reel.cover_url if reel else None

        items.append(PublicWishlistItemOut(
            listing_id=str(listing.id),
            title=listing.title,
            price=WishlistPrice(amount=listing.price_amount, currency=listing.currency),
            cover_url=cover_url,
            city=listing.city or "Москва",
            status=status_str
        ))

    next_cursor = str(items[-1].listing_id) if len(items) == limit else None

    return PublicWishlistResponse(
        owner=PublicWishlistOwner(
            display_name=owner.name or "Пользователь",
            avatar_url=owner.avatar_url
        ),
        count=total_count,
        items=items,
        next_cursor=next_cursor
    )
