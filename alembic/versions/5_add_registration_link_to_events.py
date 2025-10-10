"""Add registration_link column to events table

Revision ID: 5_add_registration_link_to_events
Revises: 4_user_connections
Create Date: 2025-09-29

"""
from alembic import op
import sqlalchemy as sa


revision = '5_add_registration_link_to_events'
down_revision = '4_user_connections'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('events')]

    # Only add column if it doesn't exist
    if 'registration_link' not in existing_columns:
        op.add_column('events', sa.Column('registration_link', sa.String(), nullable=True))
        print("✅ Added registration_link column to events table")
    else:
        print("ℹ️  registration_link column already exists in events table")


def downgrade():
    # Remove registration_link column from events table
    op.drop_column('events', 'registration_link')
