"""
Simple service to manage 2 featured event IDs as separate slots.
"""
import json
from typing import List

FEATURED_EVENTS_FILE = "initial_backend/data/featured_events.json"

def _load_featured_slots() -> dict:
    """Load featured event slots from file."""
    try:
        with open(FEATURED_EVENTS_FILE, 'r') as f:
            data = json.load(f)
            # Default structure
            return data.get('slots', {"featured_1": None, "featured_2": None})
    except (FileNotFoundError, json.JSONDecodeError):
        return {"featured_1": None, "featured_2": None}

def _save_featured_slots(slots: dict) -> None:
    """Save featured event slots to file."""
    try:
        with open(FEATURED_EVENTS_FILE, 'w') as f:
            json.dump({'slots': slots}, f, indent=2)
    except Exception as e:
        print(f"Failed to save featured slots: {e}")

def get_featured_events() -> List[dict]:
    """
    Get the featured events from both slots.
    Returns up to 2 events that are currently set as featured.
    """
    from utils.database import read_events
    slots = _load_featured_slots()

    # Load all events
    all_events = read_events()
    featured_events = []

    # Check featured_1
    if slots.get('featured_1'):
        event = next((e for e in all_events if e['id'] == slots['featured_1']), None)
        if event:
            featured_events.append(event)

    # Check featured_2
    if slots.get('featured_2'):
        event = next((e for e in all_events if e['id'] == slots['featured_2']), None)
        if event:
            featured_events.append(event)

    return featured_events

def set_featured_slot(slot: str, event_id: str = None) -> bool:
    """
    Set a specific featured slot to an event ID.
    slot should be 'featured_1' or 'featured_2'.
    Pass None to clear the slot.
    """
    if slot not in ['featured_1', 'featured_2']:
        return False

    slots = _load_featured_slots()
    slots[slot] = event_id
    _save_featured_slots(slots)
    return True

def get_featured_slot(slot: str) -> str:
    """
    Get the event ID for a specific slot.
    """
    if slot not in ['featured_1', 'featured_2']:
        return None

    slots = _load_featured_slots()
    return slots.get(slot)

def clear_featured_slot(slot: str) -> bool:
    """
    Clear a specific featured slot.
    """
    return set_featured_slot(slot, None)

def get_featured_slots() -> dict:
    """
    Get all featured slots.
    """
    return _load_featured_slots()

# Backward compatibility functions
def set_featured_events(event_ids: List[str]) -> bool:
    """
    Set featured events from a list (backward compatibility).
    Takes up to 2 event IDs.
    """
    event_ids = event_ids[:2] if event_ids else []
    slots = _load_featured_slots()

    slots['featured_1'] = event_ids[0] if len(event_ids) > 0 else None
    slots['featured_2'] = event_ids[1] if len(event_ids) > 1 else None

    _save_featured_slots(slots)
    return True

def add_featured_event(event_id: str) -> bool:
    """
    Add event to first available slot or replace featured_2.
    """
    slots = _load_featured_slots()

    if not slots['featured_1']:
        slots['featured_1'] = event_id
    else:
        slots['featured_2'] = event_id

    _save_featured_slots(slots)
    return True

def remove_featured_event(event_id: str) -> bool:
    """
    Remove event from any featured slot.
    """
    slots = _load_featured_slots()
    modified = False

    if slots['featured_1'] == event_id:
        slots['featured_1'] = None
        modified = True

    if slots['featured_2'] == event_id:
        slots['featured_2'] = None
        modified = True

    if modified:
        _save_featured_slots(slots)

    return modified

def is_event_featured(event_id: str) -> bool:
    """Check if an event is currently featured."""
    slots = _load_featured_slots()
    return event_id in [slots['featured_1'], slots['featured_2']] and event_id is not None
