from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime, timedelta
from dateutil import parser
from models.event import CreateEventIn, Event
from models.user import User
from models.ticket import Ticket
from utils.database import read_events, write_events, read_tickets, read_users
from core.config import IST
from services.qr_service import create_qr_token
from typing import List
from time import time
from services.cache_service import get_cache, set_cache, delete_cache
from services.whatsapp_service import (
    send_bulk_text,
    format_event_announcement,
    format_event_update,
)

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
            # Only expire if event is more than 1 hour in the past (safety buffer)
            if e.get("isActive", True) and end_ist_dt <= now - timedelta(hours=1):
                e["isActive"] = False
                changed = True
        except Exception:
            continue
    if changed:
        _save_events(events)

# Redis-backed cache configuration
_EVENTS_CACHE_KEY = "events:active_list"
_EVENTS_TTL_SECONDS = 300  # 5 minutes

def _cache_get_events_list():
    cached = get_cache(_EVENTS_CACHE_KEY)
    return cached

def _cache_set_events_list(value):
    set_cache(_EVENTS_CACHE_KEY, value, ttl_seconds=_EVENTS_TTL_SECONDS)

def _cache_invalidate_events_list():
    delete_cache(_EVENTS_CACHE_KEY)

@router.post("/", response_model=Event)
async def create_event(ev: CreateEventIn):
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
        createdAt=datetime.now(IST).isoformat(),
        organizerName=ev.organizerName,
        organizerLogo=ev.organizerLogo,
        coordinate_lat=ev.coordinate_lat,
        coordinate_long=ev.coordinate_long,
        address_url=ev.address_url,
        registration_link=ev.registration_link
    ).dict()

    # Save only the new event (write_events now handles upsert)
    _save_events([new_ev])
    _cache_invalidate_events_list()

    # Notify all users about new event (best effort; phones must be E.164)
    try:
        users = read_users()
        phones = [u.get("phone") for u in users if u.get("phone")]
        if phones:
            await send_bulk_text(phones, format_event_announcement(new_ev))
    except Exception:
        # Do not block event creation on messaging failures
        pass

    return new_ev

@router.get("/", response_model=List[Event])
async def list_events():
    # Cache first (Redis)
    cached = _cache_get_events_list()
    if cached is not None:
        return cached

    expire_events_if_needed()
    events = _load_events()
    now = _now_ist()
    results = []

    # Debug logging
    print(f"DEBUG: Found {len(events)} total events in database")
    print(f"DEBUG: Current IST time: {now}")

    for e in events:
        try:
            end = _to_ist(e["endAt"])
            is_active = e.get("isActive", True)
            end_in_future = end > now

            print(f"DEBUG: Event {e.get('title', 'Unknown')} - Active: {is_active}, End: {end}, End > Now: {end_in_future}")

            if is_active and end_in_future:
                results.append(Event(**e))
                print(f"DEBUG: ✓ Including event: {e.get('title', 'Unknown')}")
            else:
                print(f"DEBUG: ✗ Filtering out event: {e.get('title', 'Unknown')} (Active: {is_active}, End in future: {end_in_future})")
        except Exception as exc:
            print(f"DEBUG: ✗ Error processing event {e.get('title', 'Unknown')}: {exc}")
            continue

    print(f"DEBUG: Returning {len(results)} active future events")
    _cache_set_events_list(results)
    return results

@router.get("/recent", response_model=List[Event])
async def list_recent_events(limit: int = 10):
    """
    Get the most recent events by creation date.
    Returns up to the specified limit (default 10) of the most recently added events.
    """
    events = _load_events()
    # Sort by createdAt descending (most recent first)
    try:
        sorted_events = sorted(events, key=lambda e: parser.isoparse(e["createdAt"]), reverse=True)
    except Exception:
        # If parsing fails, fall back to original order
        sorted_events = events

    # Take the first 'limit' events
    recent_events = sorted_events[:limit]

    # Convert to Event models
    result = []
    for e in recent_events:
        try:
            result.append(Event(**e))
        except Exception:
            # Skip malformed events
            continue

    return result

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str):
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    # expire check for this event
    try:
        end = _to_ist(e["endAt"])
        if end <= _now_ist():
            e["isActive"] = False
            _save_events(events)  # Pass all events for update
            raise HTTPException(status_code=404, detail="Event expired")
    except HTTPException:
        raise
    except Exception:
        pass
    return Event(**e)

@router.get("/{event_id}/registered_users")
async def get_registered_users_for_event(event_id: str):
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
async def update_event_price(event_id: str, new_price: int):
    if new_price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    
    e["priceINR"] = new_price
    _save_events(events)  # Pass all events for update
    _cache_invalidate_events_list()
    return {"message": "Event price updated successfully", "new_price": new_price}

@router.patch("/{event_id}")
async def update_event_partial(event_id: str, event_updates: dict):
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

    # Validate organizerName if provided
    if "organizerName" in event_updates:
        organizer_name = event_updates["organizerName"]
        if organizer_name is not None and (not isinstance(organizer_name, str) or not organizer_name.strip()):
            validation_errors.append("organizerName must be a non-empty string or null")
        else:
            updated_event["organizerName"] = organizer_name

    # Validate organizerLogo if provided
    if "organizerLogo" in event_updates:
        organizer_logo = event_updates["organizerLogo"]
        if organizer_logo is not None and (not isinstance(organizer_logo, str) or not organizer_logo.strip()):
            validation_errors.append("organizerLogo must be a valid URL string or null")
        else:
            updated_event["organizerLogo"] = organizer_logo

    # Validate coordinate_lat if provided
    if "coordinate_lat" in event_updates:
        coordinate_lat = event_updates["coordinate_lat"]
        if coordinate_lat is not None and (not isinstance(coordinate_lat, str) or not coordinate_lat.strip()):
            validation_errors.append("coordinate_lat must be a valid string or null")
        else:
            updated_event["coordinate_lat"] = coordinate_lat

    # Validate coordinate_long if provided
    if "coordinate_long" in event_updates:
        coordinate_long = event_updates["coordinate_long"]
        if coordinate_long is not None and (not isinstance(coordinate_long, str) or not coordinate_long.strip()):
            validation_errors.append("coordinate_long must be a valid string or null")
        else:
            updated_event["coordinate_long"] = coordinate_long

    # Validate address_url if provided
    if "address_url" in event_updates:
        address_url = event_updates["address_url"]
        if address_url is not None and (not isinstance(address_url, str) or not address_url.strip()):
            validation_errors.append("address_url must be a valid URL string or null")
        else:
            updated_event["address_url"] = address_url

    # Validate registration_link if provided
    if "registration_link" in event_updates:
        registration_link = event_updates["registration_link"]
        if registration_link is not None and (not isinstance(registration_link, str) or not registration_link.strip()):
            validation_errors.append("registration_link must be a valid URL string or null")
        else:
            updated_event["registration_link"] = registration_link

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
    _save_events(events)  # Pass all events for update
    _cache_invalidate_events_list()

    # Notify subscribed users about update (best effort)
    try:
        # Subscribers are users whose subscribedEvents contains event_id
        users = read_users()
        subscriber_phones = [
            u.get("phone")
            for u in users
            if u.get("phone") and event_id in (u.get("subscribedEvents") or [])
        ]
        if subscriber_phones:
            await send_bulk_text(subscriber_phones, format_event_update(updated_event, list(event_updates.keys())))
    except Exception:
        pass

    # Return the updated event
    return {
        "message": "Event updated successfully",
        "event": Event(**updated_event),
        "updated_fields": list(event_updates.keys())
    }

@router.put("/{event_id}/deactivate")
async def deactivate_event(event_id: str):
    events = _load_events()
    e = next((x for x in events if x["id"] == event_id), None)
    if not e:
        raise HTTPException(status_code=404, detail="Event not found")
    if not e.get("isActive", True):
        raise HTTPException(status_code=400, detail="Event already inactive")
    e["isActive"] = False
    _save_events(events)  # Pass all events for update
    _cache_invalidate_events_list()
    return {"message": "Event deactivated successfully"}
