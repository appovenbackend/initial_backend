"""Add subscribedEvents column to users table

Revision ID: dcedd7cbabb4
Revises: 6_add_password_column_to_users
Create Date: 2025-10-06 16:18:50.537416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcedd7cbabb4'
down_revision = '6_add_password_column_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('users')]

    # Only add column if it doesn't exist
    if 'subscribedEvents' not in existing_columns:
        op.add_column('users', sa.Column('subscribedEvents', sa.Text(), nullable=True))
        print("✅ Added subscribedEvents column to users table")
    else:
        print("ℹ️  subscribedEvents column already exists in users table")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove subscribedEvents column from users table
    op.drop_column('users', 'subscribedEvents')
