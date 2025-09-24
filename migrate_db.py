#!/usr/bin/env python3
"""
Database migration script to add organizerName and organizerLogo columns to events table.
Run this script after deploying the new code to add the missing columns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import DATABASE_URL, USE_POSTGRESQL

def migrate_events_table():
    """Add organizerName, organizerLogo, coordinate_lat, coordinate_long, and address_url columns to events table"""

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
                AND column_name IN ('organizerName', 'organizerLogo', 'coordinate_lat', 'coordinate_long', 'address_url')
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

        print("🎉 Users table migration completed!")
    except Exception as e:
        print(f"❌ Users migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_events_table()
    migrate_received_qr_tokens_table()
