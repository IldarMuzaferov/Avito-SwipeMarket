from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.config import settings
from app.db.models import Event, Promotion, PromotionPlan, Reel
from app.db.session import get_db
from app.schemas.promotion import (
    EventsBatchIn,
    PromotionCreateIn,
    PromotionListOut,
    PromotionOut,
    PromotionPlanOut,
    PaymentWebhookIn,
)

router = APIRouter()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/promotion/plans", response_model=list[PromotionPlanOut])
async def get_promotion_plans(
    session: AsyncSession = Depends(get_db),
) -> list[PromotionPlanOut]:
    plans = await session.scalars(
        select(PromotionPlan).order_by(PromotionPlan.days, PromotionPlan.id)
    )
    return [
        PromotionPlanOut(
            id=str(plan.id),
            days=plan.days,
            estimated_reach=plan.estimated_reach,
            price_amount=plan.price_amount,
            is_best_value=plan.is_best_value,
        )
        for plan in plans.all()
    ]


@router.post("/reels/{reel_id}/promotions", response_model=PromotionOut)
async def create_promotion(
    reel_id: UUID,
    data: PromotionCreateIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> PromotionOut:
    user = await get_current_user(token, session)
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your reel"})
    if reel.status != "published" or not reel.enabled:
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Only published reels can be promoted"})

    plan = await session.get(PromotionPlan, data.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Promotion plan not found"})
    promotion = Promotion(
        id=uuid4(),
        reel_id=reel.id,
        plan_id=plan.id,
        status="pending_payment",
        payment_id=f"pay_{uuid4().hex}",
    )
    session.add(promotion)
    await session.commit()
    return PromotionOut(
        promotion_id=str(promotion.id),
        status=promotion.status,
        payment_url=f"{settings.MOCK_PAYMENT_BASE_URL.rstrip('/')}/{promotion.payment_id}",
        active_until=None,
    )


@router.post("/promotions/{promotion_id}/mock-pay", response_model=PromotionOut)
async def mock_pay_promotion(
    promotion_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> PromotionOut:
    user = await get_current_user(token, session)
    promotion = await session.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Promotion not found"})
    reel = await session.get(Reel, promotion.reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your promotion"})
    now = now_utc()
    if promotion.status == "active" and promotion.active_until and promotion.active_until > now:
        return PromotionOut(
            promotion_id=str(promotion.id),
            status=promotion.status,
            active_until=promotion.active_until,
        )
    if promotion.status != "pending_payment":
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Promotion cannot be paid in its current state"})
    plan = await session.get(PromotionPlan, promotion.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Promotion plan not found"})
    promotion.status = "active"
    promotion.starts_at = now
    promotion.active_until = now + timedelta(days=plan.days)
    await session.commit()
    return PromotionOut(
        promotion_id=str(promotion.id),
        status=promotion.status,
        active_until=promotion.active_until,
    )


@router.get("/reels/{reel_id}/promotions", response_model=list[PromotionListOut])
async def get_reel_promotions(
    reel_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> list[PromotionListOut]:
    user = await get_current_user(token, session)
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your reel"})
    promotions = await session.scalars(
        select(Promotion)
        .where(Promotion.reel_id == reel.id)
        .order_by(Promotion.starts_at.desc().nullslast(), Promotion.id.desc())
    )
    return [
        PromotionListOut(
            promotion_id=str(item.id),
            plan_id=str(item.plan_id),
            status=item.status,
            starts_at=item.starts_at,
            active_until=item.active_until,
        )
        for item in promotions.all()
    ]


@router.post("/events", status_code=202)
async def post_events(
    data: EventsBatchIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await get_current_user(token, session)
    reel_ids = {event.reel_id for event in data.events}
    found_ids = set(
        (await session.scalars(select(Reel.id).where(Reel.id.in_(reel_ids)))).all()
    )
    if found_ids != reel_ids:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "One or more reels were not found"})
    session.add_all(
        Event(
            id=uuid4(),
            user_id=user.id,
            reel_id=event.reel_id,
            type=event.type,
            value_ms=event.value_ms,
            ts=event.ts or now_utc(),
        )
        for event in data.events
    )
    await session.commit()
    return {"status": "accepted"}


@router.post("/payments/webhook")
async def payment_webhook(
    data: PaymentWebhookIn,
    x_payment_signature: str | None = Header(default=None, alias="X-Payment-Signature"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not x_payment_signature:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Payment signature required"})
    signed_payload = f"{data.payment_id}:{data.status}".encode()
    expected = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(x_payment_signature, expected):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Invalid payment signature"})

    promotion = await session.scalar(
        select(Promotion).where(Promotion.payment_id == data.payment_id)
    )
    if promotion is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Promotion payment not found"})
    if promotion.status != "pending_payment":
        return {"status": promotion.status}
    if data.status == "failed":
        promotion.status = "canceled"
    else:
        plan = await session.get(PromotionPlan, promotion.plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Promotion plan not found"})
        now = now_utc()
        promotion.status = "active"
        promotion.starts_at = now
        promotion.active_until = now + timedelta(days=plan.days)
    await session.commit()
    return {"status": promotion.status}
