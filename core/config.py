import os
from datetime import timedelta
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
EVENTS_FILE = os.path.join(DATA_DIR, "events.json")
TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")

# TIMEZONE
IST = ZoneInfo("Asia/Kolkata")

# SECURITY
SECRET_KEY = "supersecretkey123"   # change for prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# QR token expiry extra (seconds) - we will normally set to event end time
QR_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # fallback 24 hours
