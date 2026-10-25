from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

class UploadFileIn(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)

class UploadStartIn(BaseModel):
    kind: Literal["video", "photos"]
    files: list[UploadFileIn] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_file_count(self):
        if self.kind == "video" and len(self.files) != 1:
            raise ValueError("Exactly one video file is required")
        return self

class UploadFileOut(BaseModel):
    file_id: UUID
    put_url: str
    headers: dict

class UploadStartOut(BaseModel):
    upload_id: UUID
    files: list[UploadFileOut]
    expires_in: int

class UploadStatusOut(BaseModel):
    status: Literal["created", "uploaded", "processing", "ready", "failed"]
    error: str | None = None
    duration_sec: int | None = None
    files: list[dict] = Field(default_factory=list)

class CropIn(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def crop_inside_image(self):
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Crop rectangle must fit inside the source image")
        return self

class OrderIn(BaseModel):
    file_ids: list[UUID] = Field(min_length=1, max_length=10)

class ReelCreateIn(BaseModel):
    listing_id: UUID
    upload_id: UUID
    show_price: bool = True
    description: str | None = Field(default=None, max_length=300)

class ReelPatchIn(BaseModel):
    show_price: bool | None = None
    description: str | None = Field(default=None, max_length=300)
    enabled: bool | None = None

class ReelOut(BaseModel):
    reel_id: UUID
    listing_id: UUID
    status: str
    media_type: str
    show_price: bool
    description: str | None = None
    cover_url: str | None = None
    enabled: bool
    published_at: datetime | None = None

class ReelListOut(BaseModel):
    reel_id: UUID
    listing_id: UUID
    title: str
    price: int
    cover_url: str | None = None
    status: str
    reject_reason: str | None = None
    stats: dict
    promotion: dict

class ReelListResponse(BaseModel):
    items: list[ReelListOut]
    next_cursor: UUID | None = None

class ListingOut(BaseModel):
    id: UUID
    title: str
    price: int
    has_reel: bool
