"""Add eventId column to received_qr_tokens table

Revision ID: 1e38a8803a64
Revises: 
Create Date: 2025-09-22 18:01:50.936593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e38a8803a64'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('received_qr_tokens')]

    # Only add column if it doesn't exist
    if 'eventId' not in existing_columns:
        op.add_column('received_qr_tokens', sa.Column('eventId', sa.String(), nullable=True))
        print("✅ Added eventId column to received_qr_tokens table")
    else:
        print("ℹ️  eventId column already exists in received_qr_tokens table")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove eventId column from received_qr_tokens table
    op.drop_column('received_qr_tokens', 'eventId')
