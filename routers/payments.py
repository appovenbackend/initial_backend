from fastapi import APIRouter, HTTPException, Request, Depends
from uuid import uuid4
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional

from core.config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    RAZORPAY_WEBHOOK_SECRET,
    PAYMENT_CURRENCY,
    PAYMENT_TIMEOUT_MINUTES,
    IST,
    SECRET_KEY,
    ALGORITHM,
    JWT_KID
)
from services.payment_service import razorpay_create_order, razorpay_verify_signature
from utils.database import read_users, read_events, read_tickets, write_tickets
from services.qr_service import create_qr_token
from models.ticket import Ticket
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# In-memory payment tracking (in production, use database)
payment_orders = {}
payment_tickets = {}

def _now_ist_iso():
    return datetime.now(IST).isoformat()

def _to_ist(dt_iso: str):
    from dateutil import parser
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

@router.post("/order")
@limiter.limit("10/minute")
async def create_payment_order(request: Request, phone: str = None, eventId: str = None):
    """
    Create a Razorpay order for event payment.
    Accepts query parameters for phone and eventId.
    """
    event_id = eventId

    if not phone or not event_id:
        raise HTTPException(status_code=400, detail="phone and eventId required as query parameters")

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

        # Store order for tracking
        order_id = order_data["id"]
        payment_orders[order_id] = {
            "user_id": user["id"],
            "event_id": event_id,
            "amount": event.get("priceINR", 0),
            "created_at": _now_ist_iso(),
            "status": "created"
        }

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
@limiter.limit("20/minute")
async def verify_payment(request: Request, payload: dict):
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
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")
    phone = payload.get("phone")
    event_id = payload.get("eventId")

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

    # Update payment tracking
    if order_id in payment_orders:
        payment_orders[order_id]["status"] = "completed"
        payment_orders[order_id]["ticket_id"] = ticket_id
        payment_orders[order_id]["completed_at"] = _now_ist_iso()

    # Store ticket for webhook verification
    payment_tickets[payment_id] = new_ticket

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
@limiter.limit("100/minute")
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
            if payment_id not in payment_tickets:
                # Get order details
                if order_id in payment_orders:
                    order_info = payment_orders[order_id]
                    user_id = order_info["user_id"]
                    event_id = order_info["event_id"]

                    # Create ticket
                    ticket_id = "t_" + uuid4().hex[:10]
                    qr_token = create_qr_token(
                        ticket_id=ticket_id,
                        user_id=user_id,
                        event_id=event_id
                    )

                    new_ticket = Ticket(
                        id=ticket_id,
                        eventId=event_id,
                        userId=user_id,
                        qrToken=qr_token,
                        issuedAt=_now_ist_iso(),
                        isValidated=False,
                        validatedAt=None,
                        validationHistory=[],
                        meta={
                            "kind": "paid",
                            "amount": order_info["amount"],
                            "paymentId": payment_id,
                            "orderId": order_id,
                            "paymentMethod": method or "razorpay"
                        }
                    ).dict()

                    # Save ticket
                    tickets = read_tickets()
                    tickets.append(new_ticket)
                    write_tickets(tickets)

                    # Award legacy points for paid event registration via webhook
                    from models.user import UserPoints
                    points_to_award = UserPoints.calculate_points(order_info["amount"])
                    from utils.database import award_points_to_user
                    if award_points_to_user(user_id, points_to_award, f"Webhook payment for event (auto-created ticket)"):
                        logger.info(f"✅ Awarded {points_to_award} points to user {user_id}")
                    else:
                        logger.error(f"❌ Failed to award points to user {user_id}")

                    # Update tracking
                    payment_tickets[payment_id] = new_ticket
                    payment_orders[order_id]["status"] = "completed"
                    payment_orders[order_id]["ticket_id"] = ticket_id

                    logger.info(f"Ticket created via webhook: {ticket_id} for payment {payment_id}")

        elif event_type == "payment.captured":
            # Payment captured - mark as completed
            if order_id in payment_orders:
                payment_orders[order_id]["status"] = "captured"
                logger.info(f"Payment captured: {payment_id}")

        elif event_type == "payment.failed":
            # Payment failed - mark as failed
            if order_id in payment_orders:
                payment_orders[order_id]["status"] = "failed"
                logger.warning(f"Payment failed: {payment_id}")

        return {"status": "ok", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/orders/{order_id}")
async def get_order_status(order_id: str):
    """Get payment order status"""
    if order_id not in payment_orders:
        raise HTTPException(status_code=404, detail="Order not found")

    order_info = payment_orders[order_id]
    return {
        "order_id": order_id,
        "status": order_info["status"],
        "amount": order_info["amount"],
        "created_at": order_info["created_at"],
        "completed_at": order_info.get("completed_at"),
        "ticket_id": order_info.get("ticket_id")
    }

@router.get("/test")
async def test_payment_integration():
    """Test endpoint to verify Razorpay configuration"""
    return {
        "razorpay_configured": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),
        "key_id_configured": bool(RAZORPAY_KEY_ID),
        "webhook_configured": bool(RAZORPAY_WEBHOOK_SECRET),
        "currency": PAYMENT_CURRENCY,
        "timeout_minutes": PAYMENT_TIMEOUT_MINUTES
    }
