from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from dateutil import parser
from utils.filedb import read_users, write_users, read_events, write_events, read_tickets, write_tickets, read_received_qr_tokens, write_received_qr_tokens
from core.config import IST
from services.payment_service import create_order
from services.qr_service import create_qr_token, generate_qr_image
from models.ticket import Ticket
import json

router = APIRouter(prefix="", tags=["Tickets"])

def _load_users():
    return read_users()

def _save_users(data):
    write_users(data)

def _load_events():
    return read_events()

def _save_events(data):
    write_events(data)

def _load_tickets():
    return read_tickets()

def _save_tickets(data):
    write_tickets(data)

def _load_received_qr_tokens():
    return read_received_qr_tokens()

def _save_received_qr_tokens(data):
    write_received_qr_tokens(data)

def _now_ist_iso():
    return datetime.now(IST).isoformat()

def _to_ist(dt_iso: str):
    dt = parser.isoparse(dt_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST)

@router.post("/create-order")
def api_create_order(phone: str, eventId: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    events = _load_events()
    ev = next((e for e in events if e["id"] == eventId), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    order = create_order(eventId, ev["priceINR"])
    return order

@router.post("/register/free", response_model=Ticket)
def register_free(payload: dict):
    """
    payload: { "phone": "...", "eventId": "..." }
    """
    phone = payload.get("phone")
    eventId = payload.get("eventId")
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId = user["id"]
    events = _load_events()
    ev = next((e for e in events if e["id"] == eventId), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    # expire check
    try:
        if _to_ist(ev["endAt"]) <= datetime.now(IST) or not ev.get("isActive", True):
            raise HTTPException(status_code=400, detail="Event not active/expired")
    except HTTPException:
        raise
    # capacity check
    if ev.get("capacity", 0) > 0 and ev.get("reserved", 0) >= ev.get("capacity", 0):
        raise HTTPException(status_code=400, detail="Event full")
    # reserve seat
    ev["reserved"] = ev.get("reserved", 0) + 1
    # persist events
    all_events = _load_events()
    for i, e in enumerate(all_events):
        if e["id"] == ev["id"]:
            all_events[i] = ev
            break
    _save_events(all_events)

    # create ticket
    ticket_id = "t_" + uuid4().hex[:10]
    issued = _now_ist_iso()
    qr_token = create_qr_token(ticket_id, userId, eventId, event_end_iso_ist=ev["endAt"])
    # generate QR image file
    qr_path = generate_qr_image(qr_token, ticket_id)

    new_ticket = Ticket(
        id=ticket_id,
        eventId=eventId,
        userId=userId,
        qrToken=qr_token,
        issuedAt=issued,
        isValidated=False,
        validatedAt=None,
        validationHistory=[],
        meta={"kind": "free", "qrImagePath": qr_path}
    ).dict()

    tickets = _load_tickets()
    tickets.append(new_ticket)
    _save_tickets(tickets)
    return new_ticket

@router.post("/register/paid", response_model=Ticket)
def register_paid(payload: dict):
    """
    payload: { "phone": "...", "eventId": "...", "orderId": "..." }
    This simulates post-payment confirmation.
    """
    phone = payload.get("phone")
    eventId = payload.get("eventId")
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    userId = user["id"]
    events = _load_events()
    ev = next((e for e in events if e["id"] == eventId), None)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.get("priceINR", 0) == 0:
        raise HTTPException(status_code=400, detail="Event is free; use free register")

    ticket_id = "t_" + uuid4().hex[:10]
    issued = _now_ist_iso()
    qr_token = create_qr_token(ticket_id, userId, eventId, event_end_iso_ist=ev["endAt"])
    qr_path = generate_qr_image(qr_token, ticket_id)

    new_ticket = Ticket(
        id=ticket_id,
        eventId=eventId,
        userId=userId,
        qrToken=qr_token,
        issuedAt=issued,
        isValidated=False,
        validatedAt=None,
        validationHistory=[],
        meta={"kind": "paid", "amount": ev["priceINR"], "orderId": payload.get("orderId"), "qrImagePath": qr_path}
    ).dict()

    tickets = _load_tickets()
    tickets.append(new_ticket)
    _save_tickets(tickets)
    return new_ticket

@router.get("/tickets/{user_id}")
def get_tickets_for_user(user_id: str):
    tickets = _load_tickets()
    return [t for t in tickets if t["userId"] == user_id]

@router.get("/tickets/ticket/{ticket_id}")
def get_ticket(ticket_id: str):
    tickets = _load_tickets()
    t = next((x for x in tickets if x["id"] == ticket_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return t

@router.post("/receiveQrToken")
def receive_qr_token(token: str):
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
            "receivedAt": received_at,
            "source": None  # Add source field to match database schema
        }

        # Store in database
        received_tokens = _load_received_qr_tokens()
        received_tokens.append(new_received_token)
        _save_received_qr_tokens(received_tokens)

        return {"received_token": token, "status": "stored", "id": received_token_id, "receivedAt": received_at}
    except Exception as e:
        print(f"Error in receive_qr_token: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/getAllQrTokens")
def get_all_qr_tokens():
    """
    Retrieves all saved QR tokens from the database.
    """
    received_tokens = _load_received_qr_tokens()
    return {"qr_tokens": received_tokens, "count": len(received_tokens)}

@router.post("/validate")
def validate_token(body: dict):
    """
    Expects: { "token": "<jwt>", "device": "gate-1", "operator":"op-1" }
    Returns user + event info on first scan, or already_scanned on second.
    """
    token = body.get("token")
    device = body.get("device")
    operator = body.get("operator")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
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
    hist.append({"ts": validated_at, "device": device, "operator": operator})
    ticket["validationHistory"] = hist

    # persist tickets
    all_tickets = _load_tickets()
    for i, t in enumerate(all_tickets):
        if t["id"] == ticket["id"]:
            all_tickets[i] = ticket
            break
    _save_tickets(all_tickets)

    return {
        "status": "valid",
        "ticket_id": ticket_id,
        "user": {"id": user.get("id"), "name": user.get("name"), "phone": user.get("phone")},
        "event": ev,
        "issuedAt": ticket.get("issuedAt"),
        "validatedAt": validated_at,
        "validationHistory": ticket.get("validationHistory", [])
    }
