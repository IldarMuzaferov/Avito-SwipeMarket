"""Allow multiple reels for a listing.

Revision ID: 004_multiple_reels_per_listing
Revises: 003_audit_timestamps
"""
from alembic import op

revision = "004_multiple_reels_per_listing"
down_revision = "003_audit_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("reels_listing_id_key", "reels", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("reels_listing_id_key", "reels", ["listing_id"])
