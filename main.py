import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from routers import auth, events, tickets
from core.config import SECRET_KEY, IST
from utils.database import read_events, write_events
from datetime import datetime, timedelta
import uvicorn

def initialize_sample_data():
    """Initialize database on app startup - no sample data added to persist existing data"""
    # Database tables are created in utils.filedb.init_db()
    # No sample data is added to ensure persistence of existing data on deployment
    pass

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

@app.get("/")
def root():
    return {"msg": "Fitness Event Booking API running (times shown in IST)."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
