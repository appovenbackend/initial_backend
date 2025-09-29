#!/usr/bin/env python3
"""
Railway PostgreSQL Deployment Fix Script
Run this script to identify and fix common PostgreSQL deployment issues on Railway
"""

import os
import sys
import subprocess

def check_environment():
    """Check if required environment variables are set"""
    print("🔍 Checking Railway Environment Variables...")
    print("=" * 50)

    required_vars = [
        "DATABASE_URL",
        "JWT_SECRET",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET"
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive parts of URLs
            if "URL" in var and "://" in value:
                protocol, rest = value.split("://", 1)
                if "/" in rest:
                    host, _ = rest.split("/", 1)
                    print(f"✅ {var}: {protocol}://{host}/...")
                else:
                    print(f"✅ {var}: {value[:30]}...")
            else:
                print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("\nTo fix this:")
        print("1. Go to your Railway project dashboard")
        print("2. Navigate to 'Variables' tab")
        print("3. Add the missing variables:")
        for var in missing_vars:
            if var == "DATABASE_URL":
                print(f"   - {var}: Railway provides this automatically when you add PostgreSQL")
            elif var == "JWT_SECRET":
                print(f"   - {var}: Generate a secure random string")
            else:
                print(f"   - {var}: Add your {var.lower()} value")
        return False

    print("\n✅ All required environment variables are set!")
    return True

def test_database_connection():
    """Test database connection with current configuration"""
    print("\n🔌 Testing Database Connection...")
    print("=" * 50)

    try:
        from core.config import DATABASE_URL, USE_POSTGRESQL

        if not USE_POSTGRESQL:
            print("❌ PostgreSQL not configured (using SQLite fallback)")
            print("Make sure DATABASE_URL is set in Railway environment variables")
            return False

        # Import and test connection
        from sqlalchemy import create_engine, text

        print(f"Connecting to: {DATABASE_URL[:50]}...")
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Connection successful: {row.test}")

            # Check database version
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL version: {version[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting steps:")
        print("1. Verify DATABASE_URL is correct in Railway dashboard")
        print("2. Check if PostgreSQL database is running in Railway")
        print("3. Ensure SSL mode is properly configured")
        print("4. Check Railway logs for more details")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("\n📦 Checking Dependencies...")
    print("=" * 50)

    try:
        import fastapi
        import sqlalchemy
        import psycopg2
        import uvicorn

        print(f"✅ FastAPI: {fastapi.__version__}")
        print(f"✅ SQLAlchemy: {sqlalchemy.__version__}")
        print("✅ psycopg2: Available")
        print(f"✅ uvicorn: {uvicorn.__version__}")

        return True

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\nTo fix this:")
        print("1. Update requirements.txt with latest versions")
        print("2. Redeploy to Railway to install new dependencies")
        return False

def generate_deployment_checklist():
    """Generate a deployment checklist for the user"""
    print("\n📋 Railway Deployment Checklist")
    print("=" * 50)

    checklist = [
        "✅ Add PostgreSQL database to your Railway project",
        "✅ Set DATABASE_URL environment variable (auto-provided by Railway)",
        "✅ Set JWT_SECRET environment variable",
        "✅ Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
        "✅ Update requirements.txt with latest versions",
        "✅ Redeploy application after making changes",
        "✅ Check Railway logs for any errors",
        "✅ Test /health endpoint after deployment",
        "✅ Test /events endpoint functionality"
    ]

    for item in checklist:
        print(f"  {item}")

def main():
    """Main diagnostic function"""
    print("🚀 Railway PostgreSQL Deployment Diagnostic Tool")
    print("=" * 60)

    # Run all checks
    env_ok = check_environment()
    db_ok = test_database_connection()
    deps_ok = check_dependencies()

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    if env_ok and db_ok and deps_ok:
        print("🎉 All checks passed! Your deployment should be working.")
        print("\nNext steps:")
        print("1. Redeploy your application to Railway")
        print("2. Check the /health endpoint")
        print("3. Test the /events endpoint")
    else:
        print("⚠️  Some issues found. Please fix them and redeploy.")
        generate_deployment_checklist()

    print("\n🔗 Useful Railway Dashboard Links:")
    print("• Project Dashboard: https://railway.app/project/[your-project-id]")
    print("• Deployment Logs: Check the 'Logs' tab")
    print("• Environment Variables: Check the 'Variables' tab")
    print("• Database: Check the 'Data' tab")

if __name__ == "__main__":
    main()
