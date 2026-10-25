"""Add media upload tables and swipe undo timestamp.

Revision ID: 002_media_uploads
Revises: 001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_media_uploads"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("swipes", sa.Column("undone_at", sa.DateTime(timezone=True)))
    op.create_table(
        "media_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="created"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_uploads_user_id", "media_uploads", ["user_id"])
    op.create_table(
        "media_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "upload_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_uploads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("poster_storage_key", sa.String(1024)),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("duration_sec", sa.Integer()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crop_x", sa.Float()),
        sa.Column("crop_y", sa.Float()),
        sa.Column("crop_width", sa.Float()),
        sa.Column("crop_height", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_files_upload_id", "media_files", ["upload_id"])


def downgrade() -> None:
    op.drop_index("ix_media_files_upload_id", table_name="media_files")
    op.drop_table("media_files")
    op.drop_index("ix_media_uploads_user_id", table_name="media_uploads")
    op.drop_table("media_uploads")
    op.drop_column("swipes", "undone_at")
