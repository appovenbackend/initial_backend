"""Add isFeatured column to events table

Revision ID: 6_add_isfeatured_to_events
Revises: 5_add_registration_link_to_events
Create Date: 2025-09-29

"""
from alembic import op
import sqlalchemy as sa


revision = '6_add_isfeatured_to_events'
down_revision = '5_add_registration_link_to_events'
branch_labels = None
depends_on = None


def upgrade():
    # Add isFeatured column to events table
    op.add_column('events', sa.Column('isFeatured', sa.Boolean(), nullable=True, default=False))


def downgrade():
    # Remove isFeatured column from events table
    op.drop_column('events', 'isFeatured')
