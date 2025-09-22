"""Add source column to received_qr_tokens table

Revision ID: 2fda4990c91c
Revises: 1e38a8803a64
Create Date: 2025-09-22 18:05:23.525192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fda4990c91c'
down_revision: Union[str, Sequence[str], None] = '1e38a8803a64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add source column to received_qr_tokens table (nullable for SQLite compatibility)
    op.add_column('received_qr_tokens', sa.Column('source', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove source column from received_qr_tokens table
    op.drop_column('received_qr_tokens', 'source')
