from fastapi import APIRouter, HTTPException, Request, Header
from uuid import uuid4
from datetime import datetime
from dateutil import parser
from utils.database import read_users, write_users, read_events, write_events, read_tickets, write_tickets, read_received_qr_tokens, write_received_qr_tokens
from core.config import IST
from core.jwt_security import jwt_security_manager

from services.qr_service import create_qr_token
from services.payment_service import razorpay_verify_signature
from core.rate_limiting import api_rate_limit, auth_rate_limit
from core.rbac import require_authenticated, get_current_user_id
from models.validation import SecureFreeRegistration, SecurePaymentRequest, SecureTicketValidation
from models.ticket import Ticket
from utils.security import sql_protection, input_validator
import json
import logging
from services.cache_service import get_cache, set_cache, delete_cache
from slowapi import Limiter
from slowapi.util import get_remote_address

# Set up logging
logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes

def _get_cache(key: str):
    """Get item from Redis cache"""
    data = get_cache(key)
    if data is not None:
        logger.debug(f"Cache hit for key: {key}")
    else:
        logger.debug(f"Cache miss for key: {key}")
    return data

def _set_cache(key: str, value):
    """Set item into Redis cache"""
    set_cache(key, value, ttl_seconds=CACHE_TTL)

def _clear_cache(key: str = None):
    """Clear specific key or skip if None (no global flush here)"""
    if key:
        delete_cache(key)
        logger.debug(f"Cleared cache for key: {key}")

router = APIRouter(prefix="", tags=["Tickets"])
limiter = Limiter(key_func=get_remote_address)

def _load_users():
    cache_key = "users:all"
    cached_data = _get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    data = read_users()
    _set_cache(cache_key, data)
    return data

def _save_users(data):
    write_users(data)
    _clear_cache("users:all")  # Clear cache when data is modified

def _load_events():
    cache_key = "events:all"
    cached_data = _get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    data = read_events()
    _set_cache(cache_key, data)
    return data

def _save_events(data):
    write_events(data)
    _clear_cache("events:all")  # Clear cache when data is modified

def _load_tickets():
    cache_key = "tickets:all"
    cached_data = _get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    data = read_tickets()
    _set_cache(cache_key, data)
    return data

def _save_tickets(data):
    write_tickets(data)
    _clear_cache("tickets:all")  # Clear cache when data is modified

def _load_received_qr_tokens():
    cache_key = "qr_tokens:all"
    cached_data = _get_cache(cache_key)
    if cached_data is not None:
        return cached_data
    data = read_received_qr_tokens()
    _set_cache(cache_key, data)
    return data

def _save_received_qr_tokens(data):
    write_received_qr_tokens(data)
    _clear_cache("qr_tokens:all")  # Clear cache when data is modified

def _now_ist_iso():
    return datetime.now(IST).isoformat()

def _to_ist(dt_iso: str):
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)



@router.post("/register/free", response_model=Ticket)
@api_rate_limit("ticket_operations")
async def register_free(payload: SecureFreeRegistration, request: Request):
    """
    payload: { "phone": "...", "eventId": "..." }
    """
    phone = payload.phone
    eventId = payload.eventId
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId = user["id"]

    # Check if user has already subscribed to this event
    subscribed_events = user.get("subscribedEvents", [])
    if eventId in subscribed_events:
        raise HTTPException(status_code=400, detail="User has already subscribed to this event")

    events = _load_events()
    ev = next((e for e in events if e["id"] == eventId), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    # expire check - only check if event has ended, not if it hasn't started yet
    try:
        end_time = _to_ist(ev["endAt"])
        current_time = datetime.now(IST)

        # Only reject if event has already ended OR if event is explicitly inactive
        if end_time <= current_time or not ev.get("isActive", True):
            if end_time <= current_time:
                raise HTTPException(status_code=400, detail="Event has already ended")
            else:
                raise HTTPException(status_code=400, detail="Event is not active")
    except HTTPException:
        raise

    # capacity check
    if ev.get("capacity", 0) > 0 and ev.get("reserved", 0) >= ev.get("capacity", 0):
        raise HTTPException(status_code=400, detail="Event full")

    # Guard against duplicate free registration at ticket level as well (legacy users)
    existing_tickets = _load_tickets()
    if any(t for t in existing_tickets if t.get("userId") == userId and t.get("eventId") == eventId):
        raise HTTPException(status_code=400, detail="User already has a ticket for this event")

    # reserve seat
    ev["reserved"] = ev.get("reserved", 0) + 1
    # persist events
    all_events = _load_events()
    for i, e in enumerate(all_events):
        if e["id"] == ev["id"]:
            all_events[i] = ev
            break
    _save_events(all_events)

    # Add event to user's subscribed events
    if "subscribedEvents" not in user:
        user["subscribedEvents"] = []
    user["subscribedEvents"].append(eventId)

    # Update user record
    all_users = _load_users()
    for i, u in enumerate(all_users):
        if u["id"] == userId:
            all_users[i] = user
            break
    _save_users(all_users)

    # create ticket
    ticket_id = "t_" + uuid4().hex[:10]
    issued = _now_ist_iso()
    qr_token = create_qr_token(ticket_id, userId, eventId, event_end_iso_ist=ev["endAt"])
    new_ticket = Ticket(
        id=ticket_id,
        eventId=eventId,
        userId=userId,
        qrToken=qr_token,
        issuedAt=issued,
        isValidated=False,
        validatedAt=None,
        validationHistory=[],
        meta={"kind": "free"}
    ).dict()

    tickets = existing_tickets
    tickets.append(new_ticket)
    _save_tickets(tickets)



    return new_ticket

@router.post("/payments/verify", response_model=Ticket)
@api_rate_limit("payment")
async def payments_verify(payload: SecurePaymentRequest, request: Request):
    """Verify Razorpay signature and issue ticket on success.
    payload: { phone, eventId, razorpay_order_id, razorpay_payment_id, razorpay_signature }
    """
    phone = payload.phone
    eventId = payload.eventId
    order_id = payload.razorpay_order_id
    payment_id = payload.razorpay_payment_id
    signature = payload.razorpay_signature

    if not all([phone, eventId, order_id, payment_id, signature]):
        raise HTTPException(status_code=400, detail="Missing fields")

    if not razorpay_verify_signature(order_id, payment_id, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId = user["id"]

    events = _load_events()
    ev = next((e for e in events if e["id"] == eventId), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.get("priceINR", 0) <= 0:
        raise HTTPException(status_code=400, detail="Event is free")

    ticket_id = "t_" + uuid4().hex[:10]
    issued = _now_ist_iso()
    qr_token = create_qr_token(ticket_id, userId, eventId, event_end_iso_ist=ev["endAt"])
    new_ticket = Ticket(
        id=ticket_id,
        eventId=eventId,
        userId=userId,
        qrToken=qr_token,
        issuedAt=issued,
        isValidated=False,
        validatedAt=None,
        validationHistory=[],
        meta={"kind": "paid", "amount": ev["priceINR"], "orderId": order_id, "paymentId": payment_id}
    ).dict()

    tickets = _load_tickets()
    tickets.append(new_ticket)
    _save_tickets(tickets)

    # Award legacy points for paid event registration
    from models.user import UserPoints
    points_to_award = UserPoints.calculate_points(ev["priceINR"])
    from utils.database import award_points_to_user
    if award_points_to_user(userId, points_to_award, f"Payment verification for event: {ev['title']}"):
        print(f"✅ Awarded {points_to_award} points to user {userId}")
    else:
        print(f"❌ Failed to award points to user {userId}")

    return new_ticket

@router.get("/tickets/{user_id}")
#@api_rate_limit("authenticated")
#@require_authenticated
async def get_tickets_for_user(user_id: str, request: Request):
    # Security check - users can only view their own tickets
    current_user_id = get_current_user_id(request)
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Can only view your own tickets")
    
    tickets = _load_tickets()
    events = _load_events()

    # Enhanced response with event details
    enhanced_tickets = []
    for ticket in tickets:
        if ticket["userId"] == user_id:
            # Find corresponding event
            event = next((e for e in events if e["id"] == ticket["eventId"]), None)
            if event:
                # Add event name and other details
                ticket_with_event = ticket.copy()
                # Surface validation status consistently as snake_case too
                ticket_with_event["is_validated"] = bool(ticket.get("isValidated", False))
                ticket_with_event["eventName"] = event["title"]
                ticket_with_event["eventCity"] = event["city"]
                ticket_with_event["eventVenue"] = event["venue"]
                ticket_with_event["eventStart"] = event["startAt"]
                ticket_with_event["eventEnd"] = event["endAt"]
                enhanced_tickets.append(ticket_with_event)

    return enhanced_tickets

@router.get("/tickets/ticket/{ticket_id}")
#@api_rate_limit("authenticated")
#@require_authenticated
async def get_ticket(ticket_id: str, request: Request):
    # Security check - users can only view their own tickets
    current_user_id = get_current_user_id(request)

    tickets = _load_tickets()
    t = next((x for x in tickets if x["id"] == ticket_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t["userId"] != current_user_id:
        raise HTTPException(status_code=403, detail="Can only view your own tickets")

    # Fetch event details
    events = _load_events()
    event = next((e for e in events if e["id"] == t["eventId"]), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Return ticket with event details
    response = t.copy()
    response["is_validated"] = bool(t.get("isValidated", False))
    response["event"] = event
    return response

@router.post("/receiveQrToken")
@api_rate_limit("ticket_operations")
async def receive_qr_token(token: str, eventId: str, request: Request):
    """
    Receives QR token string from frontend and stores it in database.
    """
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")

        # Create received QR token record
        received_token_id = "rt_" + uuid4().hex[:10]
        received_at = _now_ist_iso()

        new_received_token = {
            "id": received_token_id,
            "token": token,
            "eventId": eventId,
            "receivedAt": received_at
        }

        # Store in database
        received_tokens = _load_received_qr_tokens()
        received_tokens.append(new_received_token)
        _save_received_qr_tokens(received_tokens)

        return {"received_token": token, "status": "stored", "id": received_token_id, "receivedAt": received_at, "eventId" : eventId}
    except Exception as e:
        print(f"Error in receive_qr_token: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/getAllQrTokens")
#@api_rate_limit("admin")
async def get_all_qr_tokens(request: Request):
    """
    Retrieves all saved QR tokens from the database.
    """
    received_tokens = _load_received_qr_tokens()
    return {"qr_tokens": received_tokens, "count": len(received_tokens)}

@router.get("/getQrTokensByEvent/{event_id}")
#@api_rate_limit("admin")
async def get_qr_tokens_by_event(event_id: str, request: Request):
    """
    Retrieves QR tokens for a specific event.
    """
    received_tokens = _load_received_qr_tokens()
    event_tokens = [t for t in received_tokens if t.get("eventId") == event_id]
    return {"qr_tokens": event_tokens, "count": len(event_tokens)}

from fastapi import Request

@router.post("/validate")
@api_rate_limit("ticket_operations")
async def validate_token(body: SecureTicketValidation, request: Request):
    """
    Expects: { "token": "<jwt>", "eventId": "<event_id>" }
    Returns user + event info on first scan, or already_scanned on second.
    """
    token = body.token
    eventId = body.eventId
    if not token or not eventId:
        raise HTTPException(status_code=400, detail="token and eventId required")
    # decode token safely using jose
    from jose import jwt, JWTError, ExpiredSignatureError
    from core.config import SECRET_KEY, ALGORITHM

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        return {"status": "invalid", "reason": "token_expired"}
    except JWTError:
        return {"status": "invalid", "reason": "invalid_token"}

    ticket_id = decoded.get("ticket_id")
    user_id = decoded.get("user_id")
    event_id = decoded.get("event_id")

    # Check if token's event_id matches provided eventId
    if event_id != eventId:
        return {"status": "invalid", "reason": "event_mismatch"}

    tickets = _load_tickets()
    ticket = next((t for t in tickets if t["id"] == ticket_id), None)
    if not ticket:
        return {"status": "invalid", "reason": "ticket_not_found"}

    # validate claim matches persisted record
    if ticket["userId"] != user_id or ticket["eventId"] != event_id:
        return {"status": "invalid", "reason": "claim_mismatch"}

    # check event expiry
    events = _load_events()
    ev = next((e for e in events if e["id"] == event_id), None)
    if ev:
        try:
            if _to_ist(ev["endAt"]) <= datetime.now(IST):
                return {"status": "invalid", "reason": "event_expired"}
        except Exception:
            pass

    # get user info
    users = _load_users()
    user = next((u for u in users if u["id"] == user_id), None)

    if ticket.get("isValidated", False):
        return {
            "status": "already_scanned",
            "ticket_id": ticket_id,
            "user": {"id": user.get("id"), "name": user.get("name"), "phone": user.get("phone")},
            "issuedAt": ticket.get("issuedAt"),
            "validatedAt": ticket.get("validatedAt"),
            "validationHistory": ticket.get("validationHistory", [])
        }

    # mark validated
    validated_at = _now_ist_iso()
    ticket["isValidated"] = True
    ticket["validatedAt"] = validated_at
    hist = ticket.get("validationHistory") or []
    hist.append({"ts": validated_at})
    ticket["validationHistory"] = hist

    # Award points for free events on validation (not on registration)
    points_awarded = False
    if ev and ev.get("priceINR", 0) <= 0:  # Free event
        # Check if points already awarded for this validation
        if not any(entry.get("pointsAwarded") for entry in hist[:-1]):  # Check all history except current entry
            from models.user import UserPoints
            points_to_award = UserPoints.calculate_points(ev["priceINR"])
            from utils.database import award_points_to_user
            if award_points_to_user(user_id, points_to_award, f"Free event validation for: {ev['title']}"):
                print(f"✅ Awarded {points_to_award} points to user {user_id} for free event validation")
                # Mark this validation as having awarded points
                hist[-1]["pointsAwarded"] = True
                ticket["validationHistory"] = hist
                points_awarded = True
            else:
                print(f"❌ Failed to award points to user {user_id} for free event validation")

    # persist tickets
    all_tickets = _load_tickets()
    for i, t in enumerate(all_tickets):
        if t["id"] == ticket["id"]:
            all_tickets[i] = ticket
            break
    _save_tickets(all_tickets)

    response_data = {
        "status": "valid",
        "ticket_id": ticket_id,
        "user": {"id": user.get("id"), "name": user.get("name"), "phone": user.get("phone")},
        "event": ev,
        "issuedAt": ticket.get("issuedAt"),
        "validatedAt": validated_at,
        "validationHistory": ticket.get("validationHistory", [])
    }

    if points_awarded:
        response_data["pointsAwarded"] = True

    return response_data
