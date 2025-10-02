#!/usr/bin/env python3
"""
Database migration script for Fitness Event Booking API
Handles all database schema updates for production deployment.
Run this script after deploying new code to ensure database compatibility.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Boolean
from core.config import DATABASE_URL, USE_POSTGRESQL

def migrate_events_table():
    """Add organizerName, organizerLogo, coordinate_lat, coordinate_long, address_url, and registration_link columns to events table"""

    if not USE_POSTGRESQL:
        print("⚠️  Migration only needed for PostgreSQL. Skipping for SQLite.")
        return

    if not DATABASE_URL:
        print("❌ No DATABASE_URL found. Cannot run migration.")
        return

    print("🔄 Starting database migration...")
    print(f"Database URL: {DATABASE_URL[:30]}...")

    # Create engine
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events'
                AND column_name IN ('organizerName', 'organizerLogo', 'coordinate_lat', 'coordinate_long', 'address_url', 'registration_link')
            """))

            existing_columns = [row[0] for row in result.fetchall()]

            # Add organizerName column if it doesn't exist
            if 'organizerName' not in existing_columns:
                print("📝 Adding organizerName column...")
                conn.execute(text("""
                    ALTER TABLE events
                    ADD COLUMN "organizerName" VARCHAR DEFAULT 'bhag'
                """))
                conn.commit()
                print("✅ Added organizerName column")
            else:
                print("ℹ️  organizerName column already exists")

            # Add organizerLogo column if it doesn't exist
            if 'organizerLogo' not in existing_columns:
                print("📝 Adding organizerLogo column...")
                conn.execute(text("""
                    ALTER TABLE events
                    ADD COLUMN "organizerLogo" VARCHAR DEFAULT 'https://example.com/default-logo.png'
                """))
                conn.commit()
                print("✅ Added organizerLogo column")
            else:
                print("ℹ️  organizerLogo column already exists")

            # Add coordinate_lat column if it doesn't exist
            if 'coordinate_lat' not in existing_columns:
                print("📝 Adding coordinate_lat column...")
                conn.execute(text('ALTER TABLE events ADD COLUMN "coordinate_lat" VARCHAR'))
                conn.commit()
                print("✅ Added coordinate_lat column")
            else:
                print("ℹ️  coordinate_lat column already exists")

            # Add coordinate_long column if it doesn't exist
            if 'coordinate_long' not in existing_columns:
                print("📝 Adding coordinate_long column...")
                conn.execute(text('ALTER TABLE events ADD COLUMN "coordinate_long" VARCHAR'))
                conn.commit()
                print("✅ Added coordinate_long column")
            else:
                print("ℹ️  coordinate_long column already exists")

            # Add address_url column if it doesn't exist
            if 'address_url' not in existing_columns:
                print("📝 Adding address_url column...")
                conn.execute(text('ALTER TABLE events ADD COLUMN "address_url" VARCHAR'))
                conn.commit()
                print("✅ Added address_url column")
            else:
                print("ℹ️  address_url column already exists")

            # Add registration_link column if it doesn't exist
            if 'registration_link' not in existing_columns:
                print("📝 Adding registration_link column...")
                conn.execute(text('ALTER TABLE events ADD COLUMN "registration_link" VARCHAR'))
                conn.commit()
                print("✅ Added registration_link column")
            else:
                print("ℹ️  registration_link column already exists")

        print("🎉 Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

def migrate_received_qr_tokens_table():
    """Ensure received_qr_tokens has eventId, receivedAt, source columns (PostgreSQL)."""
    if not USE_POSTGRESQL:
        print("⚠️  Migration only needed for PostgreSQL. Skipping for SQLite.")
        return

    if not DATABASE_URL:
        print("❌ No DATABASE_URL found. Cannot run migration.")
        return

    print("🔄 Starting received_qr_tokens migration...")
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            # Check existing columns
            result = conn.execute(text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'received_qr_tokens'
                """
            ))
            existing_columns = {row[0] for row in result.fetchall()}

            # Add eventId
            if 'eventId' not in existing_columns:
                print("📝 Adding eventId to received_qr_tokens...")
                conn.execute(text('ALTER TABLE received_qr_tokens ADD COLUMN "eventId" VARCHAR'))
                conn.commit()
                print("✅ Added eventId")
            else:
                print("ℹ️  eventId already exists")

            # Add receivedAt
            if 'receivedAt' not in existing_columns:
                print("📝 Adding receivedAt to received_qr_tokens...")
                conn.execute(text('ALTER TABLE received_qr_tokens ADD COLUMN "receivedAt" VARCHAR'))
                conn.commit()
                print("✅ Added receivedAt")
            else:
                print("ℹ️  receivedAt already exists")

            # Add source
            if 'source' not in existing_columns:
                print("📝 Adding source to received_qr_tokens...")
                conn.execute(text('ALTER TABLE received_qr_tokens ADD COLUMN source VARCHAR'))
                conn.commit()
                print("✅ Added source")
            else:
                print("ℹ️  source already exists")

        print("🎉 received_qr_tokens migration completed!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

def migrate_users_table():
    """Add missing columns to users table (PostgreSQL)."""
    if not USE_POSTGRESQL:
        print("⚠️  Migration only needed for PostgreSQL. Skipping for SQLite.")
        return

    if not DATABASE_URL:
        print("❌ No DATABASE_URL found. Cannot run migration.")
        return

    print("🔄 Starting users table migration...")
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            # Check existing columns
            result = conn.execute(text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users'
                """
            ))
            existing_columns = {row[0] for row in result.fetchall()}

            # Add bio column
            if 'bio' not in existing_columns:
                print("📝 Adding bio column to users...")
                conn.execute(text('ALTER TABLE users ADD COLUMN bio VARCHAR'))
                conn.commit()
                print("✅ Added bio column")
            else:
                print("ℹ️  bio column already exists")

            # Add strava_link column (corrected spelling)
            if 'strava_link' not in existing_columns:
                print("📝 Adding strava_link column to users...")
                conn.execute(text('ALTER TABLE users ADD COLUMN strava_link VARCHAR'))
                conn.commit()
                print("✅ Added strava_link column")
            else:
                print("ℹ️  strava_link column already exists")

            # Add instagram_id column
            if 'instagram_id' not in existing_columns:
                print("📝 Adding instagram_id column to users...")
                conn.execute(text('ALTER TABLE users ADD COLUMN instagram_id VARCHAR'))
                conn.commit()
                print("✅ Added instagram_id column")
            else:
                print("ℹ️  instagram_id column already exists")

            # Add is_private column for social features
            if 'is_private' not in existing_columns:
                print("📝 Adding is_private column to users...")
                conn.execute(text('ALTER TABLE users ADD COLUMN is_private BOOLEAN DEFAULT FALSE'))
                conn.commit()
                print("✅ Added is_private column")
            else:
                print("ℹ️  is_private column already exists")

            # Add password column for authentication
            if 'password' not in existing_columns:
                print("📝 Adding password column to users...")
                conn.execute(text('ALTER TABLE users ADD COLUMN password VARCHAR'))
                conn.commit()
                print("✅ Added password column")
            else:
                print("ℹ️  password column already exists")

        print("🎉 Users table migration completed!")
    except Exception as e:
        print(f"❌ Users migration failed: {e}")
        raise

def create_user_follows_table():
    """Create user_follows table for social features (PostgreSQL)."""
    if not USE_POSTGRESQL:
        print("⚠️  Migration only needed for PostgreSQL. Skipping for SQLite.")
        return

    if not DATABASE_URL:
        print("❌ No DATABASE_URL found. Cannot run migration.")
        return

    print("🔄 Creating user_follows table...")
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'user_follows'
                """
            ))
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("📝 Creating user_follows table...")
                conn.execute(text("""
                    CREATE TABLE user_follows (
                        id VARCHAR PRIMARY KEY,
                        follower_id VARCHAR NOT NULL,
                        following_id VARCHAR NOT NULL,
                        status VARCHAR NOT NULL DEFAULT 'pending',
                        created_at VARCHAR NOT NULL,
                        updated_at VARCHAR NOT NULL
                    )
                """))
                conn.commit()

                # Create indexes for performance
                conn.execute(text('CREATE INDEX idx_user_follows_follower ON user_follows(follower_id)'))
                conn.execute(text('CREATE INDEX idx_user_follows_following ON user_follows(following_id)'))
                conn.execute(text('CREATE INDEX idx_user_follows_status ON user_follows(status)'))
                conn.commit()

                print("✅ Created user_follows table with indexes")
            else:
                print("ℹ️  user_follows table already exists")

        print("🎉 User follows table creation completed!")
    except Exception as e:
        print(f"❌ User follows table creation failed: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Starting database migration for Fitness Event Booking API")
    print("=" * 60)

    try:
        migrate_events_table()
        migrate_received_qr_tokens_table()
        migrate_users_table()
        create_user_follows_table()

        print("\n" + "=" * 60)
        print("🎉 All database migrations completed successfully!")
        print("✅ Your database is now ready for production deployment.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check your DATABASE_URL and PostgreSQL connection.")
        sys.exit(1)
