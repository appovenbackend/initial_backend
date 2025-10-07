from fastapi import APIRouter, HTTPException, Request, Depends, Query
from uuid import uuid4
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional

from core.secure_config import secure_config, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, PAYMENT_CURRENCY, PAYMENT_TIMEOUT_MINUTES
from core.config import IST
from models.validation import SecurePaymentRequest
from services.payment_service import razorpay_create_order, razorpay_verify_signature
from services.payment_audit_service import payment_audit_service
from utils.database import read_users, read_events, read_tickets, write_tickets
from services.qr_service import create_qr_token
from core.rate_limiting import api_rate_limit
from middleware.jwt_auth import get_current_user_id
from utils.input_validator import input_validator
from utils.structured_logging import log_payment_attempt, track_error
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from models.ticket import Ticket

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Payment tracking now uses database with audit trail
# Removed in-memory storage for security

def _now_ist_iso():
    return datetime.now(IST).isoformat()

def _to_ist(dt_iso: str):
    from dateutil import parser
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

@router.post("/order")
@api_rate_limit("payment")
async def create_payment_order(
    request: Request,
    phone: str = Query(..., description="User phone number"),
    eventId: str = Query(..., alias="eventId", description="Event ID")
):
    """
    Create a Razorpay order for event payment.

    Query params: phone, eventId
    Returns: { "order_id": "...", "key_id": "...", "amount": 50000, "currency": "INR" }
    """
    event_id = eventId  # normalize variable name

    if not phone or not event_id:
        raise HTTPException(status_code=400, detail="phone and eventId required")
    
    # Validate input formats
    if not input_validator.validate_phone_number(phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format")
    
    if not input_validator.validate_event_id(event_id):
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    # Get user and event
    users = read_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    events = read_events()
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.get("priceINR", 0) == 0:
        raise HTTPException(status_code=400, detail="Event is free")

    # Create Razorpay order
    try:
        order_data = await razorpay_create_order(
            event_id=event_id,
            amount_inr=event.get("priceINR", 0),
            receipt=f"rcpt_{user['id']}_{event_id}"
        )

        # Store order for tracking (removed in-memory storage)
        order_id = order_data["id"]

        logger.info(f"Payment order created: {order_id} for user {user['id']}, event {event_id}")

        return {
            "order_id": order_id,
            "key_id": RAZORPAY_KEY_ID,
            "amount": order_data["amount"],
            "currency": order_data["currency"],
            "status": order_data["status"]
        }

    except Exception as e:
        logger.error(f"Failed to create payment order: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@router.post("/verify")
@api_rate_limit("payment")
async def verify_payment(request: Request, payload: SecurePaymentRequest):
    """
    Verify Razorpay payment and issue ticket.

    payload: {
        "razorpay_order_id": "...",
        "razorpay_payment_id": "...",
        "razorpay_signature": "...",
        "phone": "...",
        "eventId": "..."
    }
    """
    order_id = payload.razorpay_order_id
    payment_id = payload.razorpay_payment_id
    signature = payload.razorpay_signature
    phone = payload.phone
    event_id = payload.eventId

    if not all([order_id, payment_id, signature, phone, event_id]):
        raise HTTPException(status_code=400, detail="All payment fields required")

    # Verify signature
    if not razorpay_verify_signature(order_id, payment_id, signature):
        logger.warning(f"Invalid payment signature for order {order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Get user and event
    users = read_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    events = read_events()
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Check if ticket already exists for this payment
    tickets = read_tickets()
    existing_ticket = next(
        (t for t in tickets
         if t.get("eventId") == event_id
         and t.get("userId") == user["id"]
         and t.get("paymentId") == payment_id),
        None
    )

    if existing_ticket:
        logger.info(f"Ticket already exists for payment {payment_id}")
        return {
            "status": "success",
            "message": "Payment already verified",
            "ticket": existing_ticket
        }

    # Create server-side JWT QR token
    ticket_id = "t_" + uuid4().hex[:10]
    qr_token = create_qr_token(
        ticket_id=ticket_id,
        user_id=user["id"],
        event_id=event_id,
        event_end_iso_ist=event["endAt"]
    )

    # Create ticket with payment tracking
    new_ticket = Ticket(
        id=ticket_id,
        eventId=event_id,
        userId=user["id"],
        qrToken=qr_token,
        issuedAt=_now_ist_iso(),
        isValidated=False,
        validatedAt=None,
        validationHistory=[],
        meta={
            "kind": "paid",
            "amount": event.get("priceINR", 0),
            "paymentId": payment_id,
            "orderId": order_id,
            "paymentMethod": "razorpay"
        }
    ).dict()

    # Save ticket
    tickets.append(new_ticket)
    write_tickets(tickets)

    # Payment tracking removed - now uses database

    # Award legacy points for paid event registration
    from models.user import UserPoints
    points_to_award = UserPoints.calculate_points(event.get("priceINR", 0))
    from utils.database import award_points_to_user
    if award_points_to_user(user["id"], points_to_award, f"Payment verification for event: {event['title']}"):
        logger.info(f"✅ Awarded {points_to_award} points to user {user['id']}")
    else:
        logger.error(f"❌ Failed to award points to user {user['id']}")

    logger.info(f"Payment verified and ticket issued: {ticket_id} for payment {payment_id}")

    return {
        "status": "success",
        "message": "Payment verified successfully",
        "ticket": new_ticket,
        "qrToken": qr_token
    }

@router.post("/webhook")
@api_rate_limit("payment")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay webhook events for async payment processing.

    Webhook events: payment.authorized, payment.captured, payment.failed
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        webhook_signature = request.headers.get("X-Razorpay-Signature")

        if not webhook_signature:
            logger.warning("Missing webhook signature")
            raise HTTPException(status_code=400, detail="Missing signature")

        # Verify webhook signature
        expected_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, webhook_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse webhook payload
        payload = json.loads(body)
        event_type = payload.get("event")
        payment_data = payload.get("payload", {}).get("payment", {})

        payment_id = payment_data.get("id")
        order_id = payment_data.get("order_id")
        status = payment_data.get("status")
        method = payment_data.get("method")

        logger.info(f"Webhook received: {event_type} for payment {payment_id}")

        # Handle different event types
        if event_type == "payment.authorized":
            # Payment authorized - create ticket if not exists

            # Removed payment_orders reference
            logger.info(f"Payment authorized: {payment_id}")

        elif event_type == "payment.captured":
            # Payment captured - mark as completed
            logger.info(f"Payment captured: {payment_id}")

        elif event_type == "payment.failed":
            # Payment failed - mark as failed
            logger.warning(f"Payment failed: {payment_id}")

        return {"status": "ok", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/orders/{order_id}")
@api_rate_limit("payment")
async def get_order_status(order_id: str, request: Request):
    """Get payment order status"""
    # Removed payment_orders reference - in-memory tracking removed
    raise HTTPException(status_code=501, detail="Order tracking not implemented - removed for security")

@router.get("/test")
@api_rate_limit("admin")
async def test_payment_integration(request: Request):
    """Test endpoint to verify Razorpay configuration"""
    return {
        "razorpay_configured": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
        "key_id_configured": bool(RAZORPAY_KEY_ID),
        "webhook_configured": bool(RAZORPAY_WEBHOOK_SECRET),
        "currency": PAYMENT_CURRENCY,
        "timeout_minutes": PAYMENT_TIMEOUT_MINUTES
    }
