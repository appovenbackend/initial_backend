"""Add performance indexes for high concurrency

Revision ID: 3_performance_indexes
Revises: 2fda4990c91c
Create Date: 2025-09-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3_performance_indexes'
down_revision = '2fda4990c91c'
branch_labels = None
depends_on = None


def upgrade():
    # events composite indexes
    op.create_index('idx_events_active_city', 'events', ['isActive', 'city'], unique=False)
    op.create_index('idx_events_start_end', 'events', ['startAt', 'endAt'], unique=False)

    # tickets indexes
    op.create_index('idx_tickets_user_event', 'tickets', ['userId', 'eventId'], unique=False)
    op.create_index('idx_tickets_qr_token', 'tickets', ['qrToken'], unique=False)
    op.create_index('idx_tickets_validated_event', 'tickets', ['isValidated', 'eventId'], unique=False)

    # users composite index (phone already unique; combining with email helps fallbacks)
    op.create_index('idx_users_phone_email', 'users', ['phone', 'email'], unique=False)

    # received_qr_tokens composite for time-ordered queries by event
    op.create_index('idx_received_qr_event_received', 'received_qr_tokens', ['eventId', 'receivedAt'], unique=False)


def downgrade():
    op.drop_index('idx_received_qr_event_received', table_name='received_qr_tokens')
    op.drop_index('idx_users_phone_email', table_name='users')
    op.drop_index('idx_tickets_validated_event', table_name='tickets')
    op.drop_index('idx_tickets_qr_token', table_name='tickets')
    op.drop_index('idx_tickets_user_event', table_name='tickets')
    op.drop_index('idx_events_start_end', table_name='events')
    op.drop_index('idx_events_active_city', table_name='events')


