"""Add consistent creation and update timestamps.

Revision ID: 003_audit_timestamps
Revises: 002_media_uploads
"""
from alembic import op
import sqlalchemy as sa

revision = "003_audit_timestamps"
down_revision = "002_media_uploads"
branch_labels = None
depends_on = None

CREATED_AT_TABLES = (
    "categories",
    "user_onboarding",
    "user_interests",
    "listing_images",
    "reel_media",
    "wishlist_items",
    "wishlist_shares",
    "promotion_plans",
    "promotions",
    "events",
)
UPDATED_AT_TABLES = (
    "users",
    "user_onboarding",
    "listings",
    "reels",
    "media_files",
    "wishlist_shares",
    "promotions",
)


def upgrade() -> None:
    for table_name in CREATED_AT_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    for table_name in UPDATED_AT_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    for table_name in reversed(UPDATED_AT_TABLES):
        op.drop_column(table_name, "updated_at")
    for table_name in reversed(CREATED_AT_TABLES):
        op.drop_column(table_name, "created_at")
