from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.schemas.promotion import (
    PromotionPlanOut, PromotionCreateIn, PromotionOut,
    PromotionListOut, EventsBatchIn
)
from app.db.models import PromotionPlan, Promotion, Reel, User, Event
from app.core.security import get_current_user
from uuid import UUID, uuid4
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/promotion/plans", response_model=list[PromotionPlanOut])
async def get_promotion_plans(session: AsyncSession = Depends(get_db)):
    res = await session.execute(select(PromotionPlan))
    plans = res.scalars().all()
    return [
        PromotionPlanOut(
            id=str(p.id),
            days=p.days,
            estimated_reach=p.estimated_reach,
            price_amount=p.price_amount,
            is_best_value=p.is_best_value
        ) for p in plans
    ]

@router.post("/reels/{reel_id}/promotions", response_model=PromotionOut)
async def create_promotion(
    reel_id: str,
    data: PromotionCreateIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    reel = await session.get(Reel, UUID(reel_id))
    if not reel or reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    plan = await session.get(PromotionPlan, UUID(data.plan_id))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    promotion = Promotion(
        id=uuid4(),
        reel_id=reel.id,
        plan_id=plan.id,
        status="pending_payment",
        payment_id=f"pay_{uuid4().hex[:8]}",
        starts_at=None,
        active_until=None
    )
    session.add(promotion)
    await session.commit()

    return PromotionOut(
        promotion_id=str(promotion.id),
        status=promotion.status,
        payment_url=f"https://pay.example.com/{promotion.payment_id}",
        active_until=None
    )

@router.post("/promotions/{promotion_id}/mock-pay", response_model=PromotionOut)
async def mock_pay_promotion(
    promotion_id: str,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    promotion = await session.get(Promotion, UUID(promotion_id))
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")

    reel = await session.get(Reel, promotion.reel_id)
    if not reel or reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    plan = await session.get(PromotionPlan, promotion.plan_id)
    now = datetime.utcnow()
    promotion.status = "active"
    promotion.starts_at = now
    promotion.active_until = now + timedelta(days=plan.days)

    await session.commit()

    return PromotionOut(
        promotion_id=str(promotion.id),
        status=promotion.status,
        payment_url=None,
        active_until=promotion.active_until
    )

@router.get("/reels/{reel_id}/promotions", response_model=list[PromotionListOut])
async def get_reel_promotions(
    reel_id: str,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    reel = await session.get(Reel, UUID(reel_id))
    if not reel or reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    res = await session.execute(
        select(Promotion).where(Promotion.reel_id == reel.id)
    )
    promotions = res.scalars().all()

    return [
        PromotionListOut(
            promotion_id=str(p.id),
            plan_id=str(p.plan_id),
            status=p.status,
            starts_at=p.starts_at,
            active_until=p.active_until
        ) for p in promotions
    ]

@router.post("/events", status_code=202)
async def post_events(
    data: EventsBatchIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    events = []
    for e in data.events:
        events.append(Event(
            id=uuid4(),
            user_id=user.id,
            reel_id=UUID(e.reel_id),
            type=e.type,
            value_ms=e.value_ms,
            ts=datetime.fromisoformat(e.ts) if e.ts else datetime.utcnow()
        ))
    session.add_all(events)
    await session.commit()
    return {"status": "accepted"}
