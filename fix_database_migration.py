#!/usr/bin/env python3
"""
Database Migration Fix Script
This script adds the missing registration_link column to the events table.
Run this script to fix the production database issue.
"""

import os
import sys
from sqlalchemy import create_engine, text, Column, String, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import DATABASE_URL

Base = declarative_base()

class EventDB(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    startAt = Column(String, nullable=False)
    endAt = Column(String, nullable=False, index=True)
    priceINR = Column(Integer, nullable=False)
    bannerUrl = Column(String, nullable=True)
    isActive = Column(Boolean, default=True, index=True)
    createdAt = Column(String, nullable=False)
    organizerName = Column(String, nullable=True, default="bhag")
    organizerLogo = Column(String, nullable=True, default="https://example.com/default-logo.png")
    coordinate_lat = Column(String, nullable=True)
    coordinate_long = Column(String, nullable=True)
    address_url = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)  # New column

def fix_database():
    """Add the missing registration_link column to the events table."""

    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set!")
        print("   Make sure you're running this in your production environment.")
        return False

    try:
        print(f"🔄 Connecting to database...")
        engine = create_engine(DATABASE_URL)

        # Test connection
        with engine.connect() as conn:
            print("✅ Database connection successful!")

            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events' AND column_name = 'registration_link';
            """))

            if result.fetchone():
                print("✅ registration_link column already exists!")
                return True

            # Add the missing column
            print("🔄 Adding registration_link column...")
            conn.execute(text("ALTER TABLE events ADD COLUMN registration_link VARCHAR;"))
            conn.commit()

            print("✅ Column added successfully!")

            # Verify the column was added
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events' AND column_name = 'registration_link';
            """))

            if result.fetchone():
                print("✅ Verification successful - column exists!")
                return True
            else:
                print("❌ Verification failed - column not found!")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Database Migration Fix Script")
    print("================================")

    success = fix_database()

    if success:
        print("\n🎉 Database fix completed successfully!")
        print("   Your events API should now work properly.")
        print("   You can test it with:")
        print("   curl -X 'GET' 'https://initialbackend-production.up.railway.app/events/' -H 'accept: application/json'")
    else:
        print("\n❌ Database fix failed!")
        print("   Please check the error messages above.")

    sys.exit(0 if success else 1)
