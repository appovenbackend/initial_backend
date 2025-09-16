from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timezone
from dateutil import parser
from zoneinfo import ZoneInfo
from models.event import CreateEventIn, Event
from utils.filedb import read_json, write_json
from core.config import EVENTS_FILE
from typing import List

router = APIRouter(prefix="/events", tags=["Events"])

def _load_events():
    return read_json(EVENTS_FILE)

def _save_events(data):
    write_json(EVENTS_FILE, data)

def _now_utc():
    return datetime.now(timezone.utc)

def _to_utc(dt_iso: str):
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        # treat incoming ISO as IST when naive
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    return dt.astimezone(timezone.utc)

def expire_events_if_needed():
    events = _load_events()
    changed = False
    now = _now_utc()
    for e in events:
        try:
            end_utcdt = _to_utc(e["endAt"])
            if e.get("isActive", True) and end_utcdt <= now:
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
        createdAt=datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    ).dict()
    events.append(new_ev)
    _save_events(events)
    return new_ev

@router.get("/", response_model=List[Event])
def list_events():
    expire_events_if_needed()
    events = _load_events()
    now = _now_utc()
    results = []
    for e in events:
        try:
            end = _to_utc(e["endAt"])
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
        end = _to_utc(e["endAt"])
        if end <= _now_utc():
            e["isActive"] = False
            _save_events(events)
            raise HTTPException(status_code=404, detail="Event expired")
    except HTTPException:
        raise
    except Exception:
        pass
    return Event(**e)
