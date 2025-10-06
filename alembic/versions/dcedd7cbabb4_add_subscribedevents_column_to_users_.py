"""Add subscribedEvents column to users table

Revision ID: dcedd7cbabb4
Revises: 6_add_password_column_to_users
Create Date: 2025-10-06 16:18:50.537416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcedd7cbabb4'
down_revision: Union[str, Sequence[str], None] = '6_add_password_column_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add subscribedEvents column to users table
    op.add_column('users', sa.Column('subscribedEvents', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove subscribedEvents column from users table
    op.drop_column('users', 'subscribedEvents')
