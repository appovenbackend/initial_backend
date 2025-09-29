"""
Featured Events Service
Simple service to manage 2 featured event IDs without modifying existing schemas.
"""

import json
import os
from typing import List, Optional
from utils.database import read_events

# File to store featured event IDs
FEATURED_EVENTS_FILE = "data/featured_events.json"

def _load_featured_events() -> List[str]:
    """Load featured event IDs from file."""
    try:
        if os.path.exists(FEATURED_EVENTS_FILE):
            with open(FEATURED_EVENTS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('featured_event_ids', [])
    except Exception:
        pass
    return []

def _save_featured_events(event_ids: List[str]) -> None:
    """Save featured event IDs to file."""
    try:
        os.makedirs("data", exist_ok=True)
        with open(FEATURED_EVENTS_FILE, 'w') as f:
            json.dump({'featured_event_ids': event_ids}, f, indent=2)
    except Exception:
        pass

def get_featured_events() -> List[dict]:
    """
    Get the 2 featured events.
    Returns up to 2 events that are currently set as featured.
    """
    featured_ids = _load_featured_events()

    if not featured_ids:
        return []

    # Get all events
    all_events = read_events()

    # Find featured events
    featured_events = []
    for event in all_events:
        if event.get('id') in featured_ids:
            featured_events.append(event)
            if len(featured_events) >= 2:  # Only return up to 2
                break

    return featured_events

def set_featured_events(event_ids: List[str]) -> bool:
    """
    Set 2 events as featured.
    Accepts a list of event IDs and stores the first 2 as featured.
    """
    if not isinstance(event_ids, list):
        return False

    # Validate event IDs exist
    all_events = read_events()
    existing_ids = {event.get('id') for event in all_events}

    # Filter to only existing event IDs and take first 2
    valid_ids = [eid for eid in event_ids if eid in existing_ids][:2]

    # Save the featured event IDs
    _save_featured_events(valid_ids)
    return True

def add_featured_event(event_id: str) -> bool:
    """
    Add a single event to featured list.
    Maintains only 2 featured events maximum.
    """
    featured_ids = _load_featured_events()

    # Remove if already exists
    if event_id in featured_ids:
        featured_ids.remove(event_id)

    # Add to front and keep only 2
    featured_ids.insert(0, event_id)
    featured_ids = featured_ids[:2]

    _save_featured_events(featured_ids)
    return True

def remove_featured_event(event_id: str) -> bool:
    """
    Remove an event from featured list.
    """
    featured_ids = _load_featured_events()

    if event_id in featured_ids:
        featured_ids.remove(event_id)
        _save_featured_events(featured_ids)
        return True

    return False

def is_event_featured(event_id: str) -> bool:
    """Check if an event is currently featured."""
    featured_ids = _load_featured_events()
    return event_id in featured_ids
