"""Rename user_follows to user_connections and adjust indexes

Revision ID: 4_user_connections
Revises: 3_performance_indexes
Create Date: 2025-09-26

"""
from alembic import op
import sqlalchemy as sa


revision = '4_user_connections'
down_revision = '3_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Rename table if exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'user_follows' in tables and 'user_connections' not in tables:
        op.rename_table('user_follows', 'user_connections')

    # Recreate helpful indexes (id already primary key)
    # Drop old index names if present (safe-guard)
    try:
        op.drop_index('ix_user_follows_follower_id', table_name='user_connections')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_follows_following_id', table_name='user_connections')
    except Exception:
        pass

    # Create new indexes
    op.create_index('ix_user_connections_follower_id', 'user_connections', ['follower_id'])
    op.create_index('ix_user_connections_following_id', 'user_connections', ['following_id'])
    op.create_index('idx_user_connections_pair', 'user_connections', ['follower_id', 'following_id'], unique=False)


def downgrade():
    # Drop new indexes
    try:
        op.drop_index('idx_user_connections_pair', table_name='user_connections')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_connections_following_id', table_name='user_connections')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_connections_follower_id', table_name='user_connections')
    except Exception:
        pass

    # Rename table back if present
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'user_connections' in tables and 'user_follows' not in tables:
        op.rename_table('user_connections', 'user_follows')


