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
    # Check if column already exists before adding (for PostgreSQL compatibility)
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('users')]

    # Only add column if it doesn't exist
    if 'password' not in existing_columns:
        op.add_column('users', sa.Column('password', sa.String(), nullable=True))
        print("✅ Added password column to users table")
    else:
        print("ℹ️  password column already exists in users table")


def downgrade():
    # Remove password column from users table
    op.drop_column('users', 'password')
