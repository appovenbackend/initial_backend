"""Add requires_approval column and event_join_requests table

Revision ID: 7_add_requires_approval_and_join_requests
Revises: dcedd7cbabb4
Create Date: 2025-10-06

"""
from alembic import op
import sqlalchemy as sa


revision = '7_add_requires_approval_and_join_requests'
down_revision = 'dcedd7cbabb4'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('events')]

    # Only add column if it doesn't exist
    if 'requires_approval' not in existing_columns:
        op.add_column('events', sa.Column('requires_approval', sa.Boolean(), nullable=True, default=False))
        print("✅ Added requires_approval column to events table")
    else:
        print("ℹ️  requires_approval column already exists in events table")

    # Check if table already exists before creating
    existing_tables = inspector.get_table_names()

    # Only create table if it doesn't exist
    if 'event_join_requests' not in existing_tables:
        op.create_table(
        'event_join_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default='pending'),
        sa.Column('requested_at', sa.String(), nullable=False),
        sa.Column('reviewed_at', sa.String(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Add index for better performance
    op.create_index('ix_event_join_requests_user_id', 'event_join_requests', ['user_id'])
    op.create_index('ix_event_join_requests_event_id', 'event_join_requests', ['event_id'])


def downgrade():
    # Remove the event_join_requests table
    op.drop_index('ix_event_join_requests_event_id', table_name='event_join_requests')
    op.drop_index('ix_event_join_requests_user_id', table_name='event_join_requests')
    op.drop_table('event_join_requests')

    # Remove requires_approval column from events table
    op.drop_column('events', 'requires_approval')
