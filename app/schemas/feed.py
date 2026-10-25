from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from typing import Literal

class MediaItem(BaseModel):
    url: str
    poster: Optional[str] = None
    duration_sec: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

class Media(BaseModel):
    type: Literal["video", "photo", "album"]
    items: list[MediaItem]

class Price(BaseModel):
    amount: int
    currency: str = "RUB"

class Seller(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None
    rating: float

class FeedItem(BaseModel):
    reel_id: UUID
    listing_id: UUID
    media: Media
    title: str
    price: Optional[Price] = None
    description: str
    seller: Seller
    is_promoted: bool = False
    in_wishlist: bool = False

class FeedResponse(BaseModel):
    items: list[FeedItem]
    next_cursor: Optional[str] = None
    session_id: str

class SwipeIn(BaseModel):
    reel_id: UUID
    action: Literal["like", "dislike", "skip"]
    client_id: UUID
    session_id: Optional[str] = Field(default=None, max_length=100)
    dwell_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)
    position: int = Field(default=0, ge=0)

class SwipeOut(BaseModel):
    in_wishlist: bool
    wishlist_count: int
    swipes_total: int

class ListingPage(BaseModel):
    listing_id: UUID
    title: str
    description: str
    price: Price
    city: str
    seller: Seller
    status: Literal["available", "sold", "removed"]
    listing_url: str
    images: list[MediaItem]