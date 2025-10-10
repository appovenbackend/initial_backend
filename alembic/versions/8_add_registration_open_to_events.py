"""Add registration_open column to events table

Revision ID: 8_add_registration_open_to_events
Revises: 20251007_add_notification_templates_table
Create Date: 2025-10-07

"""
from alembic import op
import sqlalchemy as sa


revision = '8_add_registration_open_to_events'
down_revision = '7_add_requires_approval_and_join_requests'
branch_labels = None
depends_on = None


def upgrade():
    # Add registration_open column to events table
    op.add_column('events', sa.Column('registration_open', sa.Boolean(), nullable=True, default=True))


def downgrade():
    # Remove registration_open column from events table
    op.drop_column('events', 'registration_open')
