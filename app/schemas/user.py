from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class UserBase(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None

class UserOut(UserBase):
    id: UUID
    is_guest: bool
    wishlist_count: int = 0

class GuestAuthOut(BaseModel):
    access_token: str
    user: UserOut

class DemoAuthOut(BaseModel):
    access_token: str
    user: UserOut

class OnboardingOut(BaseModel):
    interests_done: bool = False
    hint_seen: bool = False

class InterestsIn(BaseModel):
    category_ids: list[UUID] = []
    skipped: bool = False

class CategoryOut(BaseModel):
    id: UUID
    name: str
    image_url: Optional[str] = None
    color: Optional[str] = None