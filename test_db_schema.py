#!/usr/bin/env python3
"""
Test script to check database schema and help debug migration issues.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.database import get_database_session, EventDB, UserDB, TicketDB, ReceivedQrTokenDB
from core.config import DATABASE_URL, USE_POSTGRESQL
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

def check_database_schema():
    """Check the current database schema against expected models"""
    print("🔍 Database Schema Investigation")
    print("=" * 50)

    print(f"Database URL: {DATABASE_URL}")
    print(f"Using PostgreSQL: {USE_POSTGRESQL}")
    print()

    if not DATABASE_URL and not USE_POSTGRESQL:
        print("❌ Using SQLite fallback")
        return

    try:
        db = get_database_session()
        print("✅ Database connection successful")

        # Test each table
        tables = [
            ("events", EventDB.__table__.name, EventDB.__table__.columns.keys()),
            ("users", UserDB.__table__.name, UserDB.__table__.columns.keys()),
            ("tickets", TicketDB.__table__.name, TicketDB.__table__.columns.keys()),
            ("received_qr_tokens", ReceivedQrTokenDB.__table__.name, ReceivedQrTokenDB.__table__.columns.keys()),
        ]

        for table_name, actual_table, expected_columns in tables:
            print(f"\n📋 Testing {table_name} table:")
            try:
                # Check if table exists
                result = db.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{actual_table}'"))
                exists = result.fetchone()
                if exists:
                    print(f"  ✅ Table '{actual_table}' exists")

                    # Get actual columns
                    result = db.execute(text(f"PRAGMA table_info({actual_table})"))
                    actual_cols = [row[1] for row in result.fetchall()]
                    print(f"  📊 Actual columns: {actual_cols}")
                    print(f"  🎯 Expected columns: {list(expected_columns)}")

                    # Check for missing columns
                    missing = [col for col in expected_columns if col not in actual_cols]
                    if missing:
                        print(f"  ❌ Missing columns: {missing}")
                    else:
                        print(f"  ✅ All expected columns present")

                else:
                    print(f"  ❌ Table '{actual_table}' does not exist")

            except Exception as e:
                print(f"  ❌ Error checking {table_name}: {str(e)}")

        db.close()
        print(f"\n✅ Schema check completed")

    except OperationalError as e:
        print(f"❌ Database connection failed: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def check_env_config():
    """Check environment configuration"""
    print("\n🌍 Environment Configuration:")
    print("-" * 30)

    env_vars = [
        'DATABASE_URL',
        'USE_POSTGRESQL'
    ]

    for var in env_vars:
        value = os.getenv(var)
        # Mask sensitive parts
        if value and 'postgres' in value.lower():
            if '@' in value:
                parts = value.split('@')
                print(f"{var}: {parts[0].split(':')[0]}:***@{parts[1][:20]}...")
            else:
                print(f"{var}: {value[:50]}...")
        else:
            print(f"{var}: {value}")

if __name__ == "__main__":
    check_env_config()
    check_database_schema()
