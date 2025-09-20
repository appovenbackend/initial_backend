import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from routers import auth, events, tickets
from core.config import SECRET_KEY, IST
from utils.database import read_events, write_events, get_database_session
from core.config import USE_POSTGRESQL, DATABASE_URL
from datetime import datetime, timedelta
import uvicorn

def initialize_sample_data():
    """Initialize database on app startup - no sample data added to ensure persistence of existing data on deployment"""
    # Database tables are created in utils.filedb.init_db()
    # No sample data is added to ensure persistence of existing data on deployment
    pass

# TEMPORARY: Run migration on startup (remove after migration completes)
def run_migration():
    """Run database migration to add organizer columns"""
    try:
        from migrate_db import migrate_events_table
        print("🔄 Running database migration on startup...")
        migrate_events_table()
        print("✅ Migration completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

run_migration()

# Initialize database on startup
initialize_sample_data()

app = FastAPI(title="Fitness Event Booking API (IST)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(tickets.router)

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"msg": "Fitness Event Booking API running (times shown in IST)."}

@app.get("/health")
def health_check():
    """Health check endpoint to verify database connection and configuration"""
    try:
        # Test database connection with a simple query
        from sqlalchemy import text
        db = get_database_session()
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        db.close()

        # Test user table exists and can be queried
        from utils.database import read_users
        users_count = len(read_users())

        return {
            "status": "healthy",
            "database": {
                "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                "postgresql_enabled": USE_POSTGRESQL,
                "database_url_present": bool(DATABASE_URL),
                "connection_test": "passed",
                "users_count": users_count
            },
            "timestamp": datetime.now(IST).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": {
                "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                "postgresql_enabled": USE_POSTGRESQL,
                "database_url_present": bool(DATABASE_URL),
                "connection_test": "failed"
            },
            "timestamp": datetime.now(IST).isoformat()
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
