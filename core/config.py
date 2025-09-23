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

# CRITICAL: Warn if using SQLite in production (DATABASE_URL should be set)
if not USE_POSTGRESQL:
    print("⚠️  WARNING: Using SQLite database! This will NOT persist data across deployments.")
    print("   Make sure DATABASE_URL environment variable is set in your production environment.")
    print("   Railway automatically provides DATABASE_URL for PostgreSQL databases.")
    print(f"   Current DATABASE_FILE: {DATABASE_FILE}")
else:
    print("✅ Using PostgreSQL database for production persistence.")

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

# CRITICAL: Warn if using default JWT secret (will break user sessions on redeploy)
if SECRET_KEY == "supersecretkey123":
    print("⚠️  WARNING: Using default JWT_SECRET! User sessions will be lost on redeployment.")
    print("   Set JWT_SECRET environment variable in your Railway deployment to persist user sessions.")
else:
    print("✅ JWT_SECRET is configured for persistent user sessions.")

# GOOGLE OAUTH
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# QR token expiry extra (seconds) - we will normally set to event end time
QR_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # fallback 24 hours

# Database Pooling Configuration (Railway-friendly; can be tuned via env)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))  # seconds
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # seconds
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
DB_POOL_USE_LIFO = os.getenv("DB_POOL_USE_LIFO", "true").lower() == "true"

# Psycopg2 connect args
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))

# External pooler (PgBouncer) toggle: if true, disable SQLAlchemy pooling
USE_PGBOUNCER = os.getenv("USE_PGBOUNCER", "false").lower() == "true"

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "localhost:6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", 0))
