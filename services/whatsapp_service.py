import os
import logging
from typing import List, Optional, Dict, Any
import httpx


logger = logging.getLogger(__name__)


WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  # Meta WhatsApp Business API token
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")  # Sender phone number ID
WHATSAPP_API_BASE = os.getenv("WHATSAPP_API_BASE", "https://graph.facebook.com/v18.0")


def _is_configured() -> bool:
    """Return True if WhatsApp credentials are configured and enabled."""
    if not WHATSAPP_ENABLED:
        logger.info("WhatsApp messaging disabled (WHATSAPP_ENABLED is false)")
        return False
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp credentials not configured. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_ID.")
        return False
    return True


async def send_whatsapp_text(phone_e164: str, text: str) -> bool:
    """Send a plain text WhatsApp message. Returns True on accepted request.

    phone_e164 should be in E.164 format (e.g., +919876543210).
    When not configured, this function is a no-op and returns False.
    """
    if not _is_configured():
        logger.info(f"[WA NOOP] Would send to {phone_e164}: {text}")
        return False

    url = f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": phone_e164,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code < 300:
                logger.info(f"WhatsApp message queued to {phone_e164}")
                return True
            else:
                logger.error(f"WhatsApp API error {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False


async def send_bulk_text(phones_e164: List[str], text: str) -> Dict[str, bool]:
    """Send text to many recipients. Returns map phone->success."""
    results: Dict[str, bool] = {}
    # Simple sequential send to keep it safe; can be optimized later with concurrency limits
    for phone in phones_e164:
        try:
            ok = await send_whatsapp_text(phone, text)
            results[phone] = ok
        except Exception as e:
            logger.error(f"Bulk send error for {phone}: {e}")
            results[phone] = False
    return results


def format_event_announcement(event: dict) -> str:
    """Human-readable message for new event announcement."""
    title = event.get("title", "New Event")
    city = event.get("city", "")
    venue = event.get("venue", "")
    start_at = event.get("startAt", "")
    end_at = event.get("endAt", "")
    return (
        f"New Event: {title}\n"
        f"City: {city}\nVenue: {venue}\n"
        f"Starts: {start_at}\nEnds: {end_at}\n"
        f"Book now in the app!"
    )


def format_event_update(event: dict, updated_fields: Optional[list] = None) -> str:
    """Human-readable message for event update notification."""
    title = event.get("title", "Event")
    fields = ", ".join(updated_fields) if updated_fields else "details"
    return (
        f"Update: {title} has new {fields}.\n"
        f"City: {event.get('city','')} | Venue: {event.get('venue','')}\n"
        f"Starts: {event.get('startAt','')} | Ends: {event.get('endAt','')}"
    )


