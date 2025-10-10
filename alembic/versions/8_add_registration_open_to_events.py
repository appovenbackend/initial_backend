"""Add registration_open column to events table

Revision ID: 8_add_registration_open_to_events
Revises: 20251007_add_notification_templates_table
Create Date: 2025-10-07

"""
from alembic import op
import sqlalchemy as sa


revision = '8_add_registration_open_to_events'
down_revision = '20251007_add_notification_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('events')]

    # Only add column if it doesn't exist
    if 'registration_open' not in existing_columns:
        op.add_column('events', sa.Column('registration_open', sa.Boolean(), nullable=True, default=True))
        print("✅ Added registration_open column to events table")
    else:
        print("ℹ️  registration_open column already exists in events table")


def downgrade():
    # Remove registration_open column from events table
    op.drop_column('events', 'registration_open')
