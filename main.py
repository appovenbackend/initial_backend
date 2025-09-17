import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, events, tickets
import uvicorn

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
