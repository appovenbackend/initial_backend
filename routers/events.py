from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime
from dateutil import parser
from models.event import CreateEventIn, Event
from models.user import User
from models.ticket import Ticket
from utils.filedb import read_events, write_events, read_tickets, read_users
from core.config import IST
from services.qr_service import create_qr_token
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

@router.get("/{event_id}/registered_users")
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

    return {
        "count": len(registered_users),
        "users": registered_users
    }

@router.put("/{event_id}/update_price")
def update_event_price(event_id: str, new_price: int):
    if new_price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    
    e["priceINR"] = new_price
    _save_events(events)
    return {"message": "Event price updated successfully", "new_price": new_price}

@router.put("/update/{event_id}")
def update_event(event_id: str, event_data: Event):
    """
    Update an existing event with complete event data.
    Returns a Ticket object as expected by the frontend.
    """
    # Validate that the event_id in path matches the id in the request body
    if event_data.id != event_id:
        raise HTTPException(status_code=400, detail="Event ID mismatch between path and body")

    # Load existing events
    events = _load_events()

    # Find the event to update
    event_index = None
    existing_event = None
    for i, e in enumerate(events):
        if e["id"] == event_id:
            event_index = i
            existing_event = e
            break

    if existing_event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Validate required fields
    if not event_data.title or not event_data.description or not event_data.city or not event_data.venue:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Validate dates
    try:
        start_dt = parser.isoparse(event_data.startAt)
        end_dt = parser.isoparse(event_data.endAt)
        if end_dt <= start_dt:
            raise HTTPException(status_code=400, detail="End date must be after start date")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Validate price
    if event_data.priceINR < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")

    # Update the event
    updated_event = event_data.dict()
    events[event_index] = updated_event
    _save_events(events)

    # Create a sample ticket response as expected by frontend
    # This is unusual for an update operation, but matches the frontend expectation
    ticket_id = "t_" + uuid4().hex[:10]
    qr_token = create_qr_token(ticket_id, "system", event_id, event_end_iso_ist=event_data.endAt)

    ticket_response = {
        "id": ticket_id,
        "eventId": event_id,
        "userId": "system",  # System user for event updates
        "qrPayload": qr_token,  # Frontend expects qrPayload, but model has qrToken
        "qrToken": qr_token,
        "createdAt": datetime.now(IST).isoformat()  # Frontend expects createdAt, but model has issuedAt
    }

    return ticket_response

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
