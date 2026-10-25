from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    city = Column(String, nullable=True)
    is_guest = Column(Boolean, default=True)
    demo_role = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    image_url = Column(String)
    color = Column(String)
    sort = Column(Integer, default=0)

class UserOnboarding(Base):
    __tablename__ = "user_onboarding"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    interests_done = Column(Boolean, default=False)
    interests_skipped = Column(Boolean, default=False)
    hint_seen = Column(Boolean, default=False)

class UserInterest(Base):
    __tablename__ = "user_interests"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), primary_key=True)

class Listing(Base):
    __tablename__ = "listings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    title = Column(String, nullable=False)
    description = Column(String)
    price_amount = Column(Integer, nullable=False)
    currency = Column(String, default="RUB")
    city = Column(String)
    status = Column(String, default="active")
    listing_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ListingImage(Base):
    __tablename__ = "listing_images"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"))
    url = Column(String)
    position = Column(Integer, default=0)

class Reel(Base):
    __tablename__ = "reels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), unique=True)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String, default="draft")
    media_type = Column(String)
    show_price = Column(Boolean, default=True)
    description = Column(String(300))
    cover_url = Column(String)
    reject_reason = Column(String)
    enabled = Column(Boolean, default=True)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReelMedia(Base):
    __tablename__ = "reel_media"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id"))
    kind = Column(String)
    url = Column(String)
    poster_url = Column(String)
    duration_sec = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    position = Column(Integer, default=0)

class Swipe(Base):
    __tablename__ = "swipes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id"))
    action = Column(String)
    client_id = Column(UUID(as_uuid=True), unique=True)
    session_id = Column(String)
    dwell_ms = Column(Integer)
    position = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"))
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_wishlist_user_listing"),)

class WishlistShare(Base):
    __tablename__ = "wishlist_shares"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    token = Column(String, unique=True)
    enabled = Column(Boolean, default=False)
    rotated_at = Column(DateTime(timezone=True))

class PromotionPlan(Base):
    __tablename__ = "promotion_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    days = Column(Integer)
    estimated_reach = Column(Integer)
    price_amount = Column(Integer)
    is_best_value = Column(Boolean, default=False)

class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id"))
    plan_id = Column(UUID(as_uuid=True), ForeignKey("promotion_plans.id"))
    status = Column(String, default="pending_payment")
    payment_id = Column(String)
    starts_at = Column(DateTime(timezone=True))
    active_until = Column(DateTime(timezone=True))

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    reel_id = Column(UUID(as_uuid=True), ForeignKey("reels.id"))
    type = Column(String)
    value_ms = Column(Integer)
    ts = Column(DateTime(timezone=True), server_default=func.now())
