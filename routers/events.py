from fastapi import APIRouter, HTTPException, Depends, Query, Request
from uuid import uuid4
from datetime import datetime, timedelta
from dateutil import parser
from core.rate_limiting import api_rate_limit, generous_rate_limit
from core.rbac import require_role, UserRole, get_current_user_id, get_current_user
from models.validation import SecureEventCreate, SecureEventUpdate
from utils.security import sql_protection, input_validator
from models.user import User
from models.ticket import Ticket
from models.event import Event
from utils.database import read_events, write_events, read_tickets, read_users, TicketDB, ReceivedQrTokenDB, EventDB
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
from services.featured_events_service import (
    get_featured_events,
    set_featured_events,
    add_featured_event,
    remove_featured_event,
    is_event_featured,
    set_featured_slot,
    get_featured_slot,
    clear_featured_slot,
    get_featured_slots,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting - must be defined before any function that uses @limiter.limit
limiter = Limiter(key_func=get_remote_address)

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
@api_rate_limit("event_creation")
async def create_event(ev: SecureEventCreate, request: Request):
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
@api_rate_limit("public_read")
async def list_events(request: Request):
    # Cache first (Redis)
    cached = _cache_get_events_list()
    if cached is not None:
        # Convert cached dicts back to Event objects
        return [Event(**event_dict) for event_dict in cached]

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
    # Cache as dictionaries, not Event objects
    _cache_set_events_list([event.dict() for event in results])
    return results

@router.get("/all", response_model=List[Event])
@api_rate_limit("admin")
async def get_all_events(request: Request):
    """
    Get ALL events including deactivated and expired events.
    This endpoint returns every event in the database regardless of active status or end date.
    Useful for admin purposes, analytics, or when you need to see historical/deactivated events.
    """
    try:
        events = _load_events()

        # Convert all events to Event models without any filtering
        result = []
        for e in events:
            try:
                result.append(Event(**e))
            except Exception as exc:
                print(f"Warning: Skipping malformed event {e.get('id', 'unknown')}: {exc}")
                continue

        print(f"DEBUG: Returning {len(result)} total events (including deactivated/expired)")
        return result

    except Exception as e:
        print(f"Error in get_all_events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve all events: {str(e)}")

@router.get("/recent", response_model=List[Event])
@api_rate_limit("public_read")
async def list_recent_events(request: Request, limit: int = 10):
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
@api_rate_limit("public_read")
async def get_event(event_id: str, request: Request):
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
@api_rate_limit("admin")
async def get_registered_users_for_event(request: Request, event_id: str):
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

    # Pre-compute which users have at least one validated ticket for this event
    validated_user_ids = set(
        t["userId"] for t in event_tickets if t.get("isValidated", False)
    )

    # Load users and include validation status
    users = read_users()
    users_with_status = []
    for u in users:
        if u["id"] in user_ids:
            user_entry = u.copy()
            user_entry["is_validated"] = u["id"] in validated_user_ids
            users_with_status.append(user_entry)

    return {
        "count": len(users_with_status),
        "users": users_with_status
    }

@router.put("/{event_id}/update_price")
@api_rate_limit("admin")
async def update_event_price(event_id: str, new_price: int, request: Request):
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
@api_rate_limit("admin")
async def update_event_partial(event_id: str, event_updates: SecureEventUpdate, request: Request):
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

    # Convert Pydantic model to dict and update only provided fields
    event_updates_dict = event_updates.dict(exclude_unset=True)
    
    # Sanitize input data
    sanitized_updates = sql_protection.validate_input(event_updates_dict)
    
    # Update fields
    for key, value in sanitized_updates.items():
        if value is not None:
            updated_event[key] = value

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
            await send_bulk_text(subscriber_phones, format_event_update(updated_event, list(sanitized_updates.keys())))
    except Exception:
        pass

    # Return the updated event
    return {
        "message": "Event updated successfully",
        "event": Event(**updated_event),
        "updated_fields": list(sanitized_updates.keys())
    }


@router.delete("/{event_id}/delete")
@api_rate_limit("admin")
async def delete_event(request: Request, event_id: str):
    """
    Delete an event completely from the database.
    This will also delete all associated tickets and received QR tokens.
    """
    from utils.database import get_database_session, read_tickets, read_received_qr_tokens

    # Check if event exists
    events = _load_events()
    event = next((x for x in events if x["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get database session for direct operations
    db = get_database_session()

    try:
        # Start transaction
        with db.begin():
            # Delete all tickets for this event
            tickets_deleted = db.query(TicketDB).filter(TicketDB.eventId == event_id).delete()

            # Delete all received QR tokens for this event
            tokens_deleted = db.query(ReceivedQrTokenDB).filter(ReceivedQrTokenDB.eventId == event_id).delete()

            # Remove event from featured slots if it exists
            current_slots = get_featured_slots()
            slots_cleared = []
            for slot_name, slot_event_id in current_slots.items():
                if slot_event_id == event_id:
                    clear_featured_slot(slot_name)
                    slots_cleared.append(slot_name)

            # Delete the event itself
            event_deleted = db.query(EventDB).filter(EventDB.id == event_id).delete()

            if event_deleted == 0:
                raise HTTPException(status_code=404, detail="Event not found")

        # Invalidate cache
        _cache_invalidate_events_list()

        return {
            "message": "Event deleted successfully",
            "event_id": event_id,
            "event_title": event.get("title"),
            "tickets_deleted": tickets_deleted,
            "tokens_deleted": tokens_deleted,
            "featured_slots_cleared": slots_cleared
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(e)}")
    finally:
        db.close()

@router.put("/{event_id}/activate")

async def activate_event(request: Request, event_id: str):
    """
    Activate a specific event by setting isActive to true.
    """
    try:
        events = _load_events()
        event = next((e for e in events if e["id"] == event_id), None)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Set event as active
        event["isActive"] = True

        # Save the updated events list
        _save_events(events)
        _cache_invalidate_events_list()

        return {
            "message": "Event activated successfully",
            "event_id": event_id,
            "event_title": event.get("title"),
            "is_active": True
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error activating event: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate event: {str(e)}")

@router.put("/{event_id}/toggle-activation")

async def toggle_event_activation(request: Request, event_id: str):
    """
    Toggle the activation status of an event.
    If event is active, it will be deactivated.
    If event is inactive, it will be activated.
    """
    try:
        events = _load_events()
        event = next((e for e in events if e["id"] == event_id), None)

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Toggle the activation status
        current_status = event.get("isActive", True)
        new_status = not current_status
        event["isActive"] = new_status

        # Save the updated events list
        _save_events(events)
        _cache_invalidate_events_list()

        # Determine action for response message
        action = "activated" if new_status else "deactivated"
        status_text = "active" if new_status else "inactive"

        return {
            "message": f"Event {action} successfully",
            "event_id": event_id,
            "event_title": event.get("title"),
            "new_status": status_text,
            "is_active": new_status
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error toggling event activation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle event activation: {str(e)}")

# New Featured Slot Management Endpoints
@router.get("/featured/slots")
async def get_featured_slots_status():
    """
    Get the current status of featured event slots.
    Returns the event IDs currently assigned to featured_1 and featured_2.
    """
    slots = get_featured_slots()

    # Get event details for non-null slots
    all_events = _load_events()
    enriched_slots = {}

    for slot_name, event_id in slots.items():
        if event_id:
            event = next((e for e in all_events if e['id'] == event_id), None)
            if event:
                enriched_slots[slot_name] = {
                    'event_id': event_id,
                    'event_title': event.get('title'),
                    'event_city': event.get('city'),
                    'event_start': event.get('startAt')
                }
            else:
                # Event not found, clear the slot
                clear_featured_slot(slot_name)
                enriched_slots[slot_name] = None
        else:
            enriched_slots[slot_name] = None

    return {"slots": enriched_slots}

@router.put("/featured/slots")
async def update_featured_slots(slots_update: dict):
    """
    Update one or both featured slots.
    Body should contain "featured_1" and/or "featured_2" with event IDs or null.
    """
    allowed_slots = {'featured_1', 'featured_2'}

    # Validate only allowed slots are provided
    invalid_keys = set(slots_update.keys()) - allowed_slots
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid slot names: {list(invalid_keys)}. Only 'featured_1' and 'featured_2' are allowed.")

    # Validate event IDs exist if provided
    all_events = _load_events()
    existing_ids = {event.get('id') for event in all_events}

    updated_slots = []

    for slot, event_id in slots_update.items():
        if event_id is not None:
            if event_id not in existing_ids:
                raise HTTPException(status_code=400, detail=f"Event ID '{event_id}' does not exist for slot '{slot}'")

        # Update the slot
        success = set_featured_slot(slot, event_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to update slot '{slot}'")

        updated_slots.append(slot)

    # Get updated slots status
    updated_status = await get_featured_slots_status()

    return {
        "message": f"Updated slots: {', '.join(updated_slots)}",
        "slots": updated_status["slots"]
    }

@router.put("/featured/slots/{slot}")
async def set_specific_featured_slot(slot: str, event_id: str = Query(None)):
    """
    Set a specific featured slot to an event ID.
    slot must be 'featured_1' or 'featured_2'.
    event_id: provide event ID to set, null to clear.
    """
    if slot not in ['featured_1', 'featured_2']:
        raise HTTPException(status_code=400, detail="Invalid slot name. Must be 'featured_1' or 'featured_2'")

    # Validate event ID if provided
    if event_id is not None:
        all_events = _load_events()
        event_exists = any(event.get('id') == event_id for event in all_events)
        if not event_exists:
            raise HTTPException(status_code=400, detail=f"Event ID '{event_id}' does not exist")

    # Update the slot
    success = set_featured_slot(slot, event_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update slot '{slot}'")

    # Get updated slots status
    updated_status = await get_featured_slots_status()

    return {
        "message": f"Slot '{slot}' updated to event ID '{event_id}'",
        "slots": updated_status["slots"]
    }

@router.delete("/featured/slots/{slot}")
async def clear_specific_featured_slot(slot: str):
    """
    Clear a specific featured slot.
    slot must be 'featured_1' or 'featured_2'.
    """
    if slot not in ['featured_1', 'featured_2']:
        raise HTTPException(status_code=400, detail="Invalid slot name. Must be 'featured_1' or 'featured_2'")

    success = clear_featured_slot(slot)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to clear slot '{slot}'")

    # Get updated slots status
    updated_status = await get_featured_slots_status()

    return {
        "message": f"Slot '{slot}' cleared",
        "slots": updated_status["slots"]
    }

# Featured Events Endpoints (existing, kept for backward compatibility)
@router.get("/featured", response_model=List[Event])
async def get_featured_events_list():
    """
    Get the 2 featured events.
    Returns up to 2 events that are currently set as featured.
    """
    try:
        featured_events_data = get_featured_events()

        # Convert to Event models
        featured_events = []
        for event_data in featured_events_data:
            try:
                featured_events.append(Event(**event_data))
            except Exception as e:
                print(f"Error converting featured event {event_data.get('id', 'unknown')}: {e}")
                continue

        return featured_events

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get featured events: {str(e)}")

@router.post("/featured")
async def set_featured_events_list(event_ids: List[str]):
    """
    Set 2 events as featured.
    Accepts a list of event IDs and stores the first 2 valid ones as featured.
    """
    try:
        if not isinstance(event_ids, list):
            raise HTTPException(status_code=400, detail="event_ids must be a list")

        if len(event_ids) == 0:
            raise HTTPException(status_code=400, detail="At least one event ID is required")

        # Validate event IDs exist
        all_events = _load_events()
        existing_ids = {event.get('id') for event in all_events}

        invalid_ids = [eid for eid in event_ids if eid not in existing_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event IDs: {invalid_ids}. These events do not exist."
            )

        # Set featured events (takes first 2)
        success = set_featured_events(event_ids)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to set featured events")

        # Get the actual featured events for response
        featured_events_data = get_featured_events()
        featured_events = [Event(**event_data) for event_data in featured_events_data]

        return {
            "message": f"Successfully set {len(featured_events)} events as featured",
            "featured_events": featured_events,
            "featured_event_ids": event_ids[:2]  # Show which IDs were actually set
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set featured events: {str(e)}")

@router.post("/featured/{event_id}")
async def toggle_featured_event(event_id: str):
    """
    Add or remove a single event from featured list.
    If event is already featured, it will be removed.
    If event is not featured, it will be added (maintaining max 2 featured events).
    """
    try:
        # Check if event exists
        all_events = _load_events()
        event_exists = any(event.get('id') == event_id for event in all_events)

        if not event_exists:
            raise HTTPException(status_code=404, detail="Event not found")

        # Check if currently featured
        currently_featured = is_event_featured(event_id)

        if currently_featured:
            # Remove from featured
            success = remove_featured_event(event_id)
            action = "removed from"
        else:
            # Add to featured
            success = add_featured_event(event_id)
            action = "added to"

        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to {action.strip()} featured events")

        # Get updated featured events
        featured_events_data = get_featured_events()
        featured_events = [Event(**event_data) for event_data in featured_events_data]

        return {
            "message": f"Event {event_id} {action} featured events",
            "currently_featured": not currently_featured,
            "featured_events": featured_events
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle featured event: {str(e)}")
