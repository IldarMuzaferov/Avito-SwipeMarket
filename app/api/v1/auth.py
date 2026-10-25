from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_guest_user,
    create_refresh_token,
    get_current_user,
    get_demo_user,
)
from app.db.models import Category, User, UserInterest, UserOnboarding, WishlistItem
from app.db.session import get_db
from app.schemas.user import (
    CategoryOut,
    DemoAuthIn,
    DemoAuthOut,
    GuestAuthIn,
    GuestAuthOut,
    InterestsIn,
    OnboardingOut,
    OnboardingPatchIn,
    UserOut,
    UserPatchIn,
    RefreshTokenIn,
)

router = APIRouter()


async def auth_response(user: User, session: AsyncSession) -> dict:
    count = await session.scalar(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
    )
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "user": {
            "id": user.id,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "city": user.city,
            "is_guest": user.is_guest,
            "wishlist_count": count or 0,
        },
    }


@router.post("/auth/guest", response_model=GuestAuthOut)
async def auth_guest(
    data: GuestAuthIn | None = None,
    session: AsyncSession = Depends(get_db),
) -> dict:
    user = await create_guest_user(session, data.name if data else None)
    return await auth_response(user, session)


@router.post("/auth/demo", response_model=DemoAuthOut)
async def auth_demo(
    data: DemoAuthIn,
    session: AsyncSession = Depends(get_db),
) -> dict:
    user = await get_demo_user(session, data.role)
    return await auth_response(user, session)


@router.get("/users/me", response_model=UserOut)
async def get_me(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    count = await session.scalar(
        select(func.count(WishlistItem.id)).where(WishlistItem.user_id == user.id)
    )
    return {
        "id": user.id,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "city": user.city,
        "is_guest": user.is_guest,
        "wishlist_count": count or 0,
    }


@router.patch("/users/me", response_model=UserOut)
async def patch_me(
    data: UserPatchIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.commit()
    return await get_me(authorization, session)


@router.post("/auth/refresh")
async def refresh_token(
    data: RefreshTokenIn,
    session: AsyncSession = Depends(get_db),
) -> dict:
    from jose import JWTError, jwt
    from app.core.config import settings

    refresh = data.refresh_token
    try:
        payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("Wrong token type")
        user_id = UUID(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid refresh token"}) from None
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "User not found"})
    return {"access_token": create_access_token({"sub": str(user.id)})}


@router.get("/categories", response_model=list[CategoryOut])
async def get_categories(session: AsyncSession = Depends(get_db)) -> list[Category]:
    result = await session.execute(select(Category).order_by(Category.sort, Category.name))
    return list(result.scalars().all())


@router.get("/users/me/onboarding", response_model=OnboardingOut)
async def get_onboarding(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    onboarding = await session.get(UserOnboarding, user.id)
    if not onboarding:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
        await session.commit()
        await session.refresh(onboarding)
    return {
        "interests_done": onboarding.interests_done,
        "hint_seen": onboarding.hint_seen,
    }


@router.put("/users/me/interests", status_code=status.HTTP_204_NO_CONTENT)
async def set_interests(
    data: InterestsIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    if data.skipped and data.category_ids:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "Choose categories or skip, not both"})
    if not data.skipped and len(set(data.category_ids)) < 3:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "Select at least three categories"})
    if data.category_ids:
        found = await session.scalars(
            select(Category.id).where(Category.id.in_(data.category_ids))
        )
        if set(found.all()) != set(data.category_ids):
            raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "Unknown category id"})

    onboarding = await session.get(UserOnboarding, user.id)
    if onboarding is None:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
    await session.execute(delete(UserInterest).where(UserInterest.user_id == user.id))
    session.add_all(
        UserInterest(user_id=user.id, category_id=category_id)
        for category_id in data.category_ids
    )
    onboarding.interests_done = True
    onboarding.interests_skipped = data.skipped
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/me/interests")
async def get_interests(
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    interests = await session.scalars(
        select(UserInterest.category_id).where(UserInterest.user_id == user.id)
    )
    return {"category_ids": list(interests.all())}


@router.patch("/users/me/onboarding", status_code=status.HTTP_204_NO_CONTENT)
async def patch_onboarding(
    data: OnboardingPatchIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})
    user = await get_current_user(authorization, session)
    onboarding = await session.get(UserOnboarding, user.id)
    if onboarding is None:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
    onboarding.hint_seen = data.hint_seen
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
