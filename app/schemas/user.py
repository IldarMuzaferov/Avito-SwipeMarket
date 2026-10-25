from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from uuid import UUID

class UserBase(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    city: Optional[str] = None

class UserOut(UserBase):
    id: UUID
    is_guest: bool
    wishlist_count: int = 0

class GuestAuthIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)

class DemoAuthIn(BaseModel):
    role: Literal["buyer", "friend", "seller"]

class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(min_length=1)

class UserPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, max_length=100)
    avatar_url: Optional[str] = Field(default=None, max_length=2048)
    city: Optional[str] = Field(default=None, max_length=100)

class GuestAuthOut(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut

class DemoAuthOut(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut

class OnboardingOut(BaseModel):
    interests_done: bool = False
    hint_seen: bool = False

class InterestsIn(BaseModel):
    category_ids: list[UUID] = Field(default_factory=list)
    skipped: bool = False

class OnboardingPatchIn(BaseModel):
    hint_seen: bool

class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    image_url: Optional[str] = None
    color: Optional[str] = None