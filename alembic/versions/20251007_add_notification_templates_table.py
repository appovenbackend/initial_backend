"""
add notification_templates table

Revision ID: 20251007_add_notification_templates
Revises: dcedd7cbabb4_add_subscribedevents_column_to_users_
Create Date: 2025-10-07 12:11:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '20251007_add_notification_templates'
down_revision = 'dcedd7cbabb4_add_subscribedevents_column_to_users_'
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = Inspector.from_engine(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, 'notification_templates'):
        return

    op.create_table(
        'notification_templates',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('template_name', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('notification_type', sa.String(), nullable=False, index=True),
        sa.Column('channel', sa.String(), nullable=False, index=True),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('variables', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('updated_at', sa.String(), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, 'notification_templates'):
        op.drop_table('notification_templates')


