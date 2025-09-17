from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime
from dateutil import parser
from models.event import CreateEventIn, Event
from models.user import User
from utils.filedb import read_events, write_events, read_tickets, read_users
from core.config import IST
from typing import List

router = APIRouter(prefix="/events", tags=["Events"])

def _load_events():
    return read_events()

def _save_events(data):
    write_events(data)

def _now_ist():
    return datetime.now(IST)

def _to_ist(dt_iso: str):
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        # treat incoming ISO as IST when naive
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

def expire_events_if_needed():
    events = _load_events()
    changed = False
    now = _now_ist()
    for e in events:
        try:
            end_ist_dt = _to_ist(e["endAt"])
            if e.get("isActive", True) and end_ist_dt <= now:
                e["isActive"] = False
                changed = True
        except Exception:
            continue
    if changed:
        _save_events(events)

@router.post("/", response_model=Event)
def create_event(ev: CreateEventIn):
    events = _load_events()
    new_ev = Event(
        id="evt_" + uuid4().hex[:10],
        title=ev.title,
        description=ev.description,
        city=ev.city,
        venue=ev.venue,
        startAt=ev.startAt,
        endAt=ev.endAt,
        priceINR=ev.priceINR,
        capacity=ev.capacity or 0,
        reserved=0,
        bannerUrl=ev.bannerUrl,
        isActive=ev.isActive if ev.isActive is not None else True,
        createdAt=datetime.now(IST).isoformat()
    ).dict()
    events.append(new_ev)
    _save_events(events)
    return new_ev

@router.get("/", response_model=List[Event])
def list_events():
    expire_events_if_needed()
    events = _load_events()
    now = _now_ist()
    results = []
    for e in events:
        try:
            end = _to_ist(e["endAt"])
            if e.get("isActive", True) and end > now:
                results.append(Event(**e))
        except Exception:
            # if malformed, skip
            continue
    return results

@router.get("/{event_id}", response_model=Event)
def get_event(event_id: str):
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    # expire check for this event
    try:
        end = _to_ist(e["endAt"])
        if end <= _now_ist():
            e["isActive"] = False
            _save_events(events)
            raise HTTPException(status_code=404, detail="Event expired")
    except HTTPException:
        raise
    except Exception:
        pass
    return Event(**e)

@router.get("/{event_id}/registered_users", response_model=List[User])
def get_registered_users_for_event(event_id: str):
    # Check if event exists
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")

    # Load tickets for this event
    tickets = read_tickets()
    event_tickets = [t for t in tickets if t["eventId"] == event_id]

    # Get unique user IDs
    user_ids = list(set(t["userId"] for t in event_tickets))

    # Load users
    users = read_users()
    registered_users = [User(**u) for u in users if u["id"] in user_ids]

    return registered_users

@router.put("/{event_id}/deactivate")
def deactivate_event(event_id: str):
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not e.get("isActive", True):
        raise HTTPException(status_code=400, detail="Event already inactive")
    e["isActive"] = False
    _save_events(events)
    return {"message": "Event deactivated successfully"}
