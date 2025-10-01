"""Add password column to users

Revision ID: 6_add_password_column_to_users
Revises: 5_add_registration_link_to_events
Create Date: 2025-10-01

"""
from alembic import op
import sqlalchemy as sa


revision = '6_add_password_column_to_users'
down_revision = '5_add_registration_link_to_events'
branch_labels = None
depends_on = None


def upgrade():
    # Add password column to users table
    op.add_column('users', sa.Column('password', sa.String(), nullable=True))


def downgrade():
    # Remove password column from users table
    op.drop_column('users', 'password')
