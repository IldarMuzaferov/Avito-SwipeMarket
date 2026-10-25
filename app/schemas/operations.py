from typing import Literal

from pydantic import BaseModel, Field


class ListingStatusIn(BaseModel):
    status: Literal["active", "sold", "removed"]


class ModerationIn(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)
