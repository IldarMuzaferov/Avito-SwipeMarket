from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class WishlistPrice(BaseModel):
    amount: int
    currency: str = "RUB"

class WishlistItemOut(BaseModel):
    listing_id: str
    reel_id: Optional[str] = None
    title: str
    price: WishlistPrice
    cover_url: Optional[str] = None
    city: str
    status: str  # available, sold, removed
    added_at: datetime

class WishlistShareOut(BaseModel):
    enabled: bool
    url: Optional[str] = None

class WishlistResponse(BaseModel):
    count: int
    items: list[WishlistItemOut]
    share: WishlistShareOut
    next_cursor: Optional[str] = None

class AddWishlistItemIn(BaseModel):
    listing_id: UUID

class ShareToggleIn(BaseModel):
    enabled: bool

class PublicWishlistOwner(BaseModel):
    display_name: str
    avatar_url: Optional[str] = None

class PublicWishlistItemOut(BaseModel):
    listing_id: str
    title: str
    price: WishlistPrice
    cover_url: Optional[str] = None
    city: str
    status: str  # available, sold

class PublicWishlistResponse(BaseModel):
    owner: PublicWishlistOwner
    count: int
    items: list[PublicWishlistItemOut]
    next_cursor: Optional[str] = None
