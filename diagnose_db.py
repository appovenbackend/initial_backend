#!/usr/bin/env python3
"""
Database diagnostic script to identify PostgreSQL connection issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from core.config import DATABASE_URL, USE_POSTGRESQL

def diagnose_database():
    """Diagnose database connection and configuration issues"""

    print("🔍 Database Diagnostic Tool")
    print("=" * 50)

    # Check if PostgreSQL is configured
    print(f"USE_POSTGRESQL: {USE_POSTGRESQL}")
    print(f"DATABASE_URL present: {bool(DATABASE_URL)}")

    if not USE_POSTGRESQL or not DATABASE_URL:
        print("❌ No PostgreSQL configuration found")
        print("Make sure DATABASE_URL environment variable is set in Railway")
        return False

    print(f"DATABASE_URL starts with: {DATABASE_URL[:50]}...")

    # Test database connection
    try:
        print("\n🔌 Testing database connection...")
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Test basic connection
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Basic connection test: {row.test}")

            # Check database version
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database version: {version[:50]}...")

            # Check if tables exist
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'events', 'tickets', 'received_qr_tokens')
            """))

            tables = [row[0] for row in result.fetchall()]
            print(f"✅ Existing tables: {tables}")

            # Check events table columns
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'events'
                ORDER BY ordinal_position
            """))

            columns = [(row[0], row[1], row[2]) for row in result.fetchall()]
            print("✅ Events table columns:")
            for col_name, data_type, is_nullable in columns:
                print(f"   - {col_name}: {data_type} {'NULL' if is_nullable == 'YES' else 'NOT NULL'}")

            # Test a simple query that might fail
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM events"))
                count = result.fetchone()[0]
                print(f"✅ Events count query successful: {count} events")
            except Exception as e:
                print(f"⚠️  Events query failed: {e}")

        print("\n✅ Database connection and basic queries successful!")
        return True

    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        print("\nPossible issues:")
        print("1. DATABASE_URL is incorrect")
        print("2. PostgreSQL instance is not running")
        print("3. Network/firewall issues")
        print("4. SSL configuration problems")
        print("5. Authentication issues")
        return False

if __name__ == "__main__":
    success = diagnose_database()
    sys.exit(0 if success else 1)
