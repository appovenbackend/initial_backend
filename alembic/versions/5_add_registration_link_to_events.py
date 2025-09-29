"""Add registration_link column to events table

Revision ID: 5_add_registration_link_to_events
Revises: 4_user_connections_table
Create Date: 2025-09-29

"""
from alembic import op
import sqlalchemy as sa


revision = '5_add_registration_link_to_events'
down_revision = '4_user_connections_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add registration_link column to events table
    op.add_column('events', sa.Column('registration_link', sa.String(), nullable=True))


def downgrade():
    # Remove registration_link column from events table
    op.drop_column('events', 'registration_link')
