from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class UploadFileIn(BaseModel):
    filename: str
    content_type: str
    size_bytes: int

class UploadStartIn(BaseModel):
    kind: str  # video or photos
    files: List[UploadFileIn]

class UploadFileOut(BaseModel):
    file_id: str
    put_url: str
    headers: dict

class UploadStartOut(BaseModel):
    upload_id: str
    files: List[UploadFileOut]
    expires_in: int

class UploadStatusOut(BaseModel):
    status: str  # created, uploaded, processing, ready, failed
    error: Optional[str] = None
    duration_sec: Optional[int] = None
    files: List[dict] = []

class CropIn(BaseModel):
    x: float
    y: float
    width: float
    height: float

class OrderIn(BaseModel):
    file_ids: List[str]

class ReelCreateIn(BaseModel):
    listing_id: str
    upload_id: str
    show_price: bool = True
    description: Optional[str] = None

class ReelOut(BaseModel):
    reel_id: str
    listing_id: str
    status: str
    media_type: str
    show_price: bool
    description: Optional[str] = None
    cover_url: Optional[str] = None
    enabled: bool
    published_at: Optional[datetime] = None

class ReelListOut(BaseModel):
    reel_id: str
    listing_id: str
    title: str
    price: int
    cover_url: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    stats: dict
    promotion: dict

class ReelListResponse(BaseModel):
    items: List[ReelListOut]
    next_cursor: Optional[str] = None

class ListingOut(BaseModel):
    id: str
    title: str
    price: int
    has_reel: bool
