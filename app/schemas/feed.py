from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class MediaItem(BaseModel):
    url: str
    poster: Optional[str] = None
    duration_sec: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

class Media(BaseModel):
    type: str  # video, photo, album
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
    reel_id: str
    listing_id: str
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
    reel_id: str
    action: str  # like, dislike, skip
    client_id: str
    session_id: Optional[str] = None
    dwell_ms: Optional[int] = None
    position: int = 0

class SwipeOut(BaseModel):
    in_wishlist: bool
    wishlist_count: int
    swipes_total: int

class ListingPage(BaseModel):
    listing_id: str
    title: str
    description: str
    price: Price
    city: str
    seller: Seller
    status: str  # available, sold
    listing_url: str
    images: list[MediaItem]