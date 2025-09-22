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
    # Add eventId column to received_qr_tokens table (nullable first for SQLite compatibility)
    op.add_column('received_qr_tokens', sa.Column('eventId', sa.String(), nullable=True))
    # Update existing records with a default value if needed
    # For now, we'll leave existing records as NULL and make the column NOT NULL in a future migration
    # when we have proper data migration logic


def downgrade() -> None:
    """Downgrade schema."""
    # Remove eventId column from received_qr_tokens table
    op.drop_column('received_qr_tokens', 'eventId')
