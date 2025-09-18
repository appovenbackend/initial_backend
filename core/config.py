import os
from datetime import timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_FILE = os.path.join(DATA_DIR, "app.db")

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
