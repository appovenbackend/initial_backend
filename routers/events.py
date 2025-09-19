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

@router.patch("/{event_id}")
def update_event_partial(event_id: str, event_updates: dict):
    """
    Update an existing event with partial data.
    Only provided fields will be updated, others remain unchanged.
    Supports flexible updates for better frontend integration.
    """
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

    # Create a copy of existing event to modify
    updated_event = existing_event.copy()

    # Validate and update only provided fields
    validation_errors = []

    # Validate title if provided
    if "title" in event_updates:
        if not event_updates["title"] or not event_updates["title"].strip():
            validation_errors.append("Title cannot be empty")
        else:
            updated_event["title"] = event_updates["title"].strip()

    # Validate description if provided
    if "description" in event_updates:
        if not event_updates["description"] or not event_updates["description"].strip():
            validation_errors.append("Description cannot be empty")
        else:
            updated_event["description"] = event_updates["description"].strip()

    # Validate city if provided
    if "city" in event_updates:
        if not event_updates["city"] or not event_updates["city"].strip():
            validation_errors.append("City cannot be empty")
        else:
            updated_event["city"] = event_updates["city"].strip()

    # Validate venue if provided
    if "venue" in event_updates:
        if not event_updates["venue"] or not event_updates["venue"].strip():
            validation_errors.append("Venue cannot be empty")
        else:
            updated_event["venue"] = event_updates["venue"].strip()

    # Validate dates if provided
    if "startAt" in event_updates or "endAt" in event_updates:
        start_date = event_updates.get("startAt", updated_event["startAt"])
        end_date = event_updates.get("endAt", updated_event["endAt"])

        try:
            start_dt = parser.isoparse(start_date)
            end_dt = parser.isoparse(end_date)
            if end_dt <= start_dt:
                validation_errors.append("End date must be after start date")
            else:
                updated_event["startAt"] = start_date
                updated_event["endAt"] = end_date
        except Exception:
            validation_errors.append("Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

    # Validate price if provided
    if "priceINR" in event_updates:
        try:
            price = int(event_updates["priceINR"])
            if price < 0:
                validation_errors.append("Price cannot be negative")
            else:
                updated_event["priceINR"] = price
        except (ValueError, TypeError):
            validation_errors.append("Price must be a valid number")

    # Validate bannerUrl if provided
    if "bannerUrl" in event_updates:
        # Allow empty bannerUrl (optional field)
        updated_event["bannerUrl"] = event_updates["bannerUrl"]

    # Validate isActive if provided
    if "isActive" in event_updates:
        try:
            is_active = bool(event_updates["isActive"])
            updated_event["isActive"] = is_active
        except (ValueError, TypeError):
            validation_errors.append("isActive must be a boolean value")

    # Check for validation errors
    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Validation failed",
                "errors": validation_errors
            }
        )

    # Preserve the original createdAt timestamp
    updated_event["createdAt"] = existing_event["createdAt"]

    # Update the event in the list
    events[event_index] = updated_event
    _save_events(events)

    # Return the updated event
    return {
        "message": "Event updated successfully",
        "event": Event(**updated_event),
        "updated_fields": list(event_updates.keys())
    }

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
