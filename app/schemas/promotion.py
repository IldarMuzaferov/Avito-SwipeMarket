from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PromotionPlanOut(BaseModel):
    id: str
    days: int
    estimated_reach: int
    price_amount: int
    is_best_value: bool

class PromotionCreateIn(BaseModel):
    plan_id: str

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
    type: str
    reel_id: str
    value_ms: Optional[int] = None
    ts: Optional[str] = None

class EventsBatchIn(BaseModel):
    events: list[EventIn]
