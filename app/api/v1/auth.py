from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import GuestAuthOut, DemoAuthOut, UserOut, OnboardingOut, InterestsIn
from app.core.security import create_access_token, create_guest_user, get_demo_user, get_current_user
from app.db.models import User, UserOnboarding, UserInterest, Category

router = APIRouter()

@router.post("/auth/guest", response_model=GuestAuthOut)
async def auth_guest(name: str | None = None, session: AsyncSession = Depends(get_db)):
    user = await create_guest_user(session, name)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "user": {
        "id": user.id, "name": user.name, "avatar_url": user.avatar_url,
        "city": user.city, "is_guest": user.is_guest, "wishlist_count": 0
    }}

@router.post("/auth/demo", response_model=DemoAuthOut)
async def auth_demo(role: str, session: AsyncSession = Depends(get_db)):
    if role not in ("buyer", "friend", "seller"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user = await get_demo_user(session, role)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "user": {
        "id": user.id, "name": user.name, "avatar_url": user.avatar_url,
        "city": user.city, "is_guest": user.is_guest, "wishlist_count": 0
    }}

@router.get("/users/me", response_model=UserOut)
async def get_me(token: str, session: AsyncSession = Depends(get_db)):
    user = await get_current_user(token, session)
    return {
        "id": user.id, "name": user.name, "avatar_url": user.avatar_url,
        "city": user.city, "is_guest": user.is_guest, "wishlist_count": 0
    }

@router.get("/categories")
async def get_categories(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Category).order_by(Category.sort))
    categories = result.scalars().all()
    return [{"id": c.id, "name": c.name, "image_url": c.image_url, "color": c.color} for c in categories]

@router.get("/users/me/onboarding", response_model=OnboardingOut)
async def get_onboarding(token: str, session: AsyncSession = Depends(get_db)):
    user = await get_current_user(token, session)
    result = await session.execute(select(UserOnboarding).where(UserOnboarding.user_id == user.id))
    onboarding = result.scalar_one_or_none()
    if not onboarding:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
        await session.commit()
    return {"interests_done": onboarding.interests_done, "hint_seen": onboarding.hint_seen}

@router.put("/users/me/interests")
async def set_interests(data: InterestsIn, token: str, session: AsyncSession = Depends(get_db)):
    user = await get_current_user(token, session)
    onboarding = await session.get(UserOnboarding, user.id)
    if not onboarding:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
    if data.skipped:
        onboarding.interests_skipped = True
        onboarding.interests_done = True
    else:
        if len(data.category_ids) < 3:
            raise HTTPException(status_code=400, detail="Need at least 3 categories")
        await session.execute(
            UserInterest.__table__.delete().where(UserInterest.user_id == user.id)
        )
        for cat_id in data.category_ids:
            session.add(UserInterest(user_id=user.id, category_id=cat_id))
        onboarding.interests_done = True
        onboarding.interests_skipped = False
    await session.commit()
    return {"status": "ok"}

@router.get("/users/me/interests")
async def get_interests(token: str, session: AsyncSession = Depends(get_db)):
    user = await get_current_user(token, session)
    result = await session.execute(
        select(UserInterest).where(UserInterest.user_id == user.id)
    )
    interests = result.scalars().all()
    return {"category_ids": [i.category_id for i in interests]}

@router.patch("/users/me/onboarding")
async def patch_onboarding(hint_seen: bool, token: str, session: AsyncSession = Depends(get_db)):
    user = await get_current_user(token, session)
    onboarding = await session.get(UserOnboarding, user.id)
    if not onboarding:
        onboarding = UserOnboarding(user_id=user.id)
        session.add(onboarding)
    onboarding.hint_seen = hint_seen
    await session.commit()
    return {"status": "ok"}