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
    """Add organizerName and organizerLogo columns to events table"""

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
                AND column_name IN ('organizerName', 'organizerLogo')
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

        print("🎉 Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_events_table()
