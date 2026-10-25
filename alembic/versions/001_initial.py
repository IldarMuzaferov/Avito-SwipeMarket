"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('is_guest', sa.Boolean(), default=True),
        sa.Column('demo_role', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('image_url', sa.String()),
        sa.Column('color', sa.String()),
        sa.Column('sort', sa.Integer(), default=0)
    )
    
    op.create_table('user_onboarding',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('interests_done', sa.Boolean(), default=False),
        sa.Column('interests_skipped', sa.Boolean(), default=False),
        sa.Column('hint_seen', sa.Boolean(), default=False)
    )
    
    op.create_table('user_interests',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), primary_key=True)
    )
    
    op.create_table('listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('seller_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id')),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('price_amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(), default='RUB'),
        sa.Column('city', sa.String()),
        sa.Column('status', sa.String(), default='active'),
        sa.Column('listing_url', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_listings_status_category', 'listings', ['status', 'category_id'])
    
    op.create_table('listing_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('listings.id')),
        sa.Column('url', sa.String()),
        sa.Column('position', sa.Integer(), default=0)
    )
    
    op.create_table('reels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('listings.id'), unique=True),
        sa.Column('seller_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('status', sa.String(), default='draft'),
        sa.Column('media_type', sa.String()),
        sa.Column('show_price', sa.Boolean(), default=True),
        sa.Column('description', sa.String(300)),
        sa.Column('cover_url', sa.String()),
        sa.Column('reject_reason', sa.String()),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_reels_status_published', 'reels', ['status', 'published_at'])
    
    op.create_table('reel_media',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reels.id')),
        sa.Column('kind', sa.String()),
        sa.Column('url', sa.String()),
        sa.Column('poster_url', sa.String()),
        sa.Column('duration_sec', sa.Integer()),
        sa.Column('width', sa.Integer()),
        sa.Column('height', sa.Integer()),
        sa.Column('position', sa.Integer(), default=0)
    )
    
    op.create_table('swipes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('reel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reels.id')),
        sa.Column('action', sa.String()),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), unique=True),
        sa.Column('session_id', sa.String()),
        sa.Column('dwell_ms', sa.Integer()),
        sa.Column('position', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_swipes_user_reel_created', 'swipes', ['user_id', 'reel_id', 'created_at'])
    
    op.create_table('wishlist_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('listings.id')),
        sa.Column('reel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reels.id')),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_unique_constraint('uq_wishlist_user_listing', 'wishlist_items', ['user_id', 'listing_id'])
    
    op.create_table('wishlist_shares',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('token', sa.String(), unique=True),
        sa.Column('enabled', sa.Boolean(), default=False),
        sa.Column('rotated_at', sa.DateTime(timezone=True))
    )
    
    op.create_table('promotion_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('days', sa.Integer()),
        sa.Column('estimated_reach', sa.Integer()),
        sa.Column('price_amount', sa.Integer()),
        sa.Column('is_best_value', sa.Boolean(), default=False)
    )
    
    op.create_table('promotions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('reel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reels.id')),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('promotion_plans.id')),
        sa.Column('status', sa.String(), default='pending_payment'),
        sa.Column('payment_id', sa.String()),
        sa.Column('starts_at', sa.DateTime(timezone=True)),
        sa.Column('active_until', sa.DateTime(timezone=True))
    )
    
    op.create_table('events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('reel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reels.id')),
        sa.Column('type', sa.String()),
        sa.Column('value_ms', sa.Integer()),
        sa.Column('ts', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    op.create_index('idx_events_reel_type', 'events', ['reel_id', 'type'])

def downgrade():
    op.drop_table('events')
    op.drop_table('promotions')
    op.drop_table('promotion_plans')
    op.drop_table('wishlist_shares')
    op.drop_table('wishlist_items')
    op.drop_table('swipes')
    op.drop_table('reel_media')
    op.drop_table('reels')
    op.drop_table('listing_images')
    op.drop_table('listings')
    op.drop_table('user_interests')
    op.drop_table('user_onboarding')
    op.drop_table('categories')
    op.drop_table('users')