from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, events, tickets
from threading import Lock

# Global lock for file operations (used by all modules)
file_lock = Lock()

app = FastAPI(title="Fitness Event Booking API (IST)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(tickets.router)

@app.get("/")
def root():
    return {"msg": "Fitness Event Booking API running (times shown in IST)."}
