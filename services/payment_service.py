from uuid import uuid4
import base64
import hmac
import hashlib
from typing import Optional
import httpx
import os

from core.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


async def razorpay_create_order(event_id: str, amount_inr: int, receipt: Optional[str] = None) -> dict:
    """Create a Razorpay order in paise. Returns JSON response or raises.

    amount_inr: integer rupees. Converted to paise for Razorpay.
    """
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        # Fallback: mock order for local dev
        return {
            "id": "order_" + uuid4().hex[:12],
            "amount": amount_inr * 100,
            "currency": "INR",
            "status": "created",
            "notes": {"eventId": event_id},
        }

    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    payload = {
        "amount": amount_inr * 100,
        "currency": "INR",
        "receipt": receipt or ("rcpt_" + uuid4().hex[:10]),
        "notes": {"eventId": event_id},
    }
    async with httpx.AsyncClient(timeout=15, auth=auth) as client:
        r = await client.post("https://api.razorpay.com/v1/orders", json=payload)
        r.raise_for_status()
        return r.json()


def razorpay_verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay signature: HMAC_SHA256(order_id|payment_id)."""
    if not RAZORPAY_KEY_SECRET:
        return False
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
