"""Merge parallel migration branches

Revision ID: d170ece3cf6a
Revises: 7_add_requires_approval_and_join_requests, 8_add_registration_open_to_events
Create Date: 2025-10-10 15:56:53.146633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd170ece3cf6a'
down_revision: Union[str, Sequence[str], None] = ('7_add_requires_approval_and_join_requests', '8_add_registration_open_to_events')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
