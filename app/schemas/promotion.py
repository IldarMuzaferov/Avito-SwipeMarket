from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

class PromotionPlanOut(BaseModel):
    id: str
    days: int
    estimated_reach: int
    price_amount: int
    is_best_value: bool

class PromotionCreateIn(BaseModel):
    plan_id: UUID

class PromotionOut(BaseModel):
    promotion_id: str
    status: str
    payment_url: Optional[str] = None
    active_until: Optional[datetime] = None

class PromotionListOut(BaseModel):
    promotion_id: str
    plan_id: str
    status: str
    starts_at: Optional[datetime] = None
    active_until: Optional[datetime] = None

class EventIn(BaseModel):
    type: Literal["view", "watch", "expand_description", "open_listing", "sound_toggle"]
    reel_id: UUID
    value_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)
    ts: Optional[datetime] = None

class EventsBatchIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=100)

class PaymentWebhookIn(BaseModel):
    payment_id: str = Field(min_length=1, max_length=100)
    status: Literal["paid", "failed"]
