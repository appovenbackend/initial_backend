import os
from datetime import timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Database configuration for Railway deployment
DATABASE_URL = os.getenv("DATABASE_URL")  # Railway PostgreSQL
DATABASE_FILE = os.path.join(DATA_DIR, "app.db")  # Local SQLite fallback

# Fix postgres scheme and add sslmode=require if missing (Railway compatibility)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

# If deploying on Railway Postgres, enforce sslmode
if DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

# Use PostgreSQL if DATABASE_URL is provided (Railway), otherwise use SQLite
USE_POSTGRESQL = bool(DATABASE_URL)

# Debug logging for database configuration
print("=== DATABASE CONFIGURATION ===")
print(f"DATABASE_URL present: {bool(DATABASE_URL)}")
print(f"USE_POSTGRESQL: {USE_POSTGRESQL}")
if DATABASE_URL:
    print(f"DATABASE_URL starts with: {DATABASE_URL[:20]}...")
else:
    print(f"Using SQLite: {DATABASE_FILE}")
print("===============================")

# TIMEZONE
IST = timezone(timedelta(hours=5, minutes=30))

# SECURITY
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey123")   # change for prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# GOOGLE OAUTH
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# QR token expiry extra (seconds) - we will normally set to event end time
QR_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # fallback 24 hours
