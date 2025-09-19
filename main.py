import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from routers import auth, events, tickets
from core.config import SECRET_KEY, IST
from utils.filedb import read_events, write_events
from datetime import datetime, timedelta
import uvicorn

def initialize_sample_data():
    """Initialize sample free events on app startup"""
    events = read_events()

    # Only add sample data if no events exist
    if len(events) == 0:
        print("Initializing sample free events...")

        # Create some sample free events
        sample_events = [
            {
                "id": "evt_sample_001",
                "title": "Free Yoga Session",
                "description": "Join us for a relaxing yoga session in the park. Perfect for beginners and experienced practitioners alike.",
                "city": "Mumbai",
                "venue": "Marine Drive Park",
                "startAt": (datetime.now(IST) + timedelta(days=7)).isoformat(),
                "endAt": (datetime.now(IST) + timedelta(days=7, hours=2)).isoformat(),
                "priceINR": 0,
                "bannerUrl": "https://example.com/yoga-banner.jpg",
                "isActive": True,
                "createdAt": datetime.now(IST).isoformat()
            },
            {
                "id": "evt_sample_002",
                "title": "Free Zumba Dance Class",
                "description": "Get your heart pumping with our energetic Zumba dance class! No experience required.",
                "city": "Delhi",
                "venue": "Connaught Place Community Center",
                "startAt": (datetime.now(IST) + timedelta(days=10)).isoformat(),
                "endAt": (datetime.now(IST) + timedelta(days=10, hours=1, minutes=30)).isoformat(),
                "priceINR": 0,
                "bannerUrl": "https://example.com/zumba-banner.jpg",
                "isActive": True,
                "createdAt": datetime.now(IST).isoformat()
            },
            {
                "id": "evt_sample_003",
                "title": "Free Meditation Workshop",
                "description": "Learn mindfulness techniques and meditation practices to reduce stress and improve focus.",
                "city": "Bangalore",
                "venue": "Cubbon Park Pavilion",
                "startAt": (datetime.now(IST) + timedelta(days=14)).isoformat(),
                "endAt": (datetime.now(IST) + timedelta(days=14, hours=1)).isoformat(),
                "priceINR": 0,
                "bannerUrl": "https://example.com/meditation-banner.jpg",
                "isActive": True,
                "createdAt": datetime.now(IST).isoformat()
            },
            {
                "id": "evt_sample_004",
                "title": "Free HIIT Workout",
                "description": "High-Intensity Interval Training session to boost your metabolism and fitness level.",
                "city": "Chennai",
                "venue": "Marina Beach Sports Complex",
                "startAt": (datetime.now(IST) + timedelta(days=5)).isoformat(),
                "endAt": (datetime.now(IST) + timedelta(days=5, hours=1)).isoformat(),
                "priceINR": 0,
                "bannerUrl": "https://example.com/hiit-banner.jpg",
                "isActive": True,
                "createdAt": datetime.now(IST).isoformat()
            },
            {
                "id": "evt_sample_005",
                "title": "Free Pilates Class",
                "description": "Strengthen your core and improve flexibility with our guided Pilates session.",
                "city": "Pune",
                "venue": "Aundh Gymkhana",
                "startAt": (datetime.now(IST) + timedelta(days=3)).isoformat(),
                "endAt": (datetime.now(IST) + timedelta(days=3, hours=1, minutes=30)).isoformat(),
                "priceINR": 0,
                "bannerUrl": "https://example.com/pilates-banner.jpg",
                "isActive": True,
                "createdAt": datetime.now(IST).isoformat()
            }
        ]

        write_events(sample_events)
        print(f"Added {len(sample_events)} sample free events")

# Initialize sample data on startup
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
