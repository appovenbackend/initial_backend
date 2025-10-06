from fastapi import APIRouter, HTTPException, Depends, Request, Header
from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from core.rate_limiting import api_rate_limit
from core.rbac import require_authenticated, get_current_user_id, require_role, UserRole
from core.jwt_security import jwt_security_manager
from utils.security import sql_protection, input_validator
from models.user import User
from models.user_follow import (
    UserConnection, ConnectionRequest, ConnectionResponse,
    UserProfileResponse, ConnectionRequestItem
)
from utils.database import (
    read_users, write_users, read_user_follows, write_user_follows,
    read_events, read_tickets
)
from core.config import IST
import json
from services.whatsapp_service import send_bulk_text

router = APIRouter(prefix="/social", tags=["Social"])

def _load_users():
    return read_users()

def _save_users(data):
    write_users(data)

def _load_user_follows():
    return read_user_follows()

def _save_user_follows(data):
    write_user_follows(data)

def _now_ist():
    return datetime.now(IST).isoformat()


def _get_relationship_status(current_user_id: str, target_user_id: str, connections: list) -> dict:
    """Return connection status between two users in the new connection model."""
    # Check for accepted connection (either direction) - always visible
    accepted = next(
        (c for c in connections if c['status'] == 'accepted' and (
            (c['follower_id'] == current_user_id and c['following_id'] == target_user_id) or
            (c['follower_id'] == target_user_id and c['following_id'] == current_user_id)
        )),
        None
    )

    if accepted:
        return {
            'is_connected': True,
            'connection_status': 'accepted'
        }

    # For pending requests, only show to the receiver (target), not the sender
    # This ensures privacy - senders cannot see their own pending requests
    incoming_pending = next(
        (c for c in connections
         if c['follower_id'] == current_user_id and c['following_id'] == target_user_id and c['status'] == 'pending'),
        None
    )

    return {
        'is_connected': False,
        'connection_status': None  # Hide pending status from sender
    }

def _can_view_profile(viewer_id: str, target_user: dict, connections: list) -> bool:
    """Check if viewer can see target's full profile"""
    is_private = bool(target_user.get('is_private', False))
    if not is_private:
        return True  # Public profile

    # Check if there is an accepted connection (either direction)
    accepted = next((c for c in connections if c['status'] == 'accepted' and (
        (c['follower_id'] == viewer_id and c['following_id'] == target_user['id']) or
        (c['follower_id'] == target_user['id'] and c['following_id'] == viewer_id)
    )), None)

    return accepted is not None

def _build_profile_response(user: dict, viewer_id: str = None, connections: list = None) -> UserProfileResponse:
    """Build profile response with privacy controls"""
    if not connections:
        connections = []

    # Get follower/following counts
    connections_count = len([c for c in connections if c['status'] == 'accepted' and (
        c['following_id'] == user['id'] or c['follower_id'] == user['id']
    )])


    # Check if viewer can see full profile
    can_view_full_profile = viewer_id and _can_view_profile(viewer_id, user, connections)
    
    # Base response - always show public info
    response_data = {
        'id': user['id'],
        'name': user['name'],
        'is_private': user.get('is_private', False),
        'connections_count': connections_count,
        'created_at': user['createdAt'],
        'picture': None,
        'bio': None,
        'strava_link': None,
        'instagram_id': None,
        'subscribed_events': None
    }

    # Add private info based on privacy settings
    if not user.get('is_private', False) or can_view_full_profile:
        # Public profile OR viewer has accepted connection
        response_data.update({
            'picture': user.get('picture'),
            'bio': user.get('bio'),
            'strava_link': user.get('strava_link'),
            'instagram_id': user.get('instagram_id'),
            'subscribed_events': user.get('subscribedEvents', [])
        })

    response = UserProfileResponse(**response_data)

    # Add relationship status if viewer is specified
    if viewer_id:
        relationship = _get_relationship_status(viewer_id, user['id'], connections)
        response.is_connected = relationship['is_connected']
        response.connection_status = relationship['connection_status']

    return response

@router.get("/users/{user_id}", response_model=UserProfileResponse)
@api_rate_limit("social_operations")
@require_authenticated
async def get_user_profile(
    user_id: str,
    request: Request
):
    """Get user profile with privacy controls"""
    current_user_id = get_current_user_id(request)

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()
    return _build_profile_response(user, current_user_id, follows)

@router.get("/users/{user_id}/privacy")
@api_rate_limit("social_operations")
async def get_privacy_setting(
    user_id: str,
    request: Request
):
    """Get the current privacy setting for a user"""
    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_private = bool(user.get('is_private', False))
    return {"user_id": user_id, "is_private": is_private}

@router.put("/users/{user_id}/privacy")
@api_rate_limit("social_operations")
@require_authenticated
async def update_privacy_setting(
    user_id: str,
    request: Request,
):
    """Toggle the user's account privacy setting"""
    current_user_id = get_current_user_id(request)

    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Can only toggle your own privacy settings")

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle the privacy setting
    user['is_private'] = not user.get('is_private', False)
    _save_users(users)

    new_state = user['is_private']
    return {"message": f"Account toggled to {'private' if new_state else 'public'}", "is_private": new_state}

@router.post("/users/{user_id}/connect", response_model=ConnectionResponse)
@api_rate_limit("social_operations")
@require_authenticated
async def request_connection(
    user_id: str,
    request: Request
):
    """Request a connection; if target is public, auto-accept."""
    current_user_id = get_current_user_id(request)

    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")

    users = _load_users()
    target_user = next((u for u in users if u['id'] == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()

    # Check if existing connection or request FROM current user TO target user only
    existing = next((c for c in follows if (
        c['follower_id'] == current_user_id and c['following_id'] == user_id
    )), None)

    if existing:
        if existing['status'] == 'accepted':
            raise HTTPException(status_code=400, detail="Already connected")
        elif existing['status'] == 'pending':
            raise HTTPException(status_code=400, detail="Connection request already pending")

    # Check privacy status more carefully with explicit boolean conversion
    is_private = bool(target_user.get('is_private', False))

    # Create follow relationship
    now = _now_ist()
    connection_status = 'accepted' if not is_private else 'pending'

    new_follow = {
        'id': f"conn_{uuid4().hex[:10]}",
        'follower_id': current_user_id,
        'following_id': user_id,
        'status': connection_status,
        'created_at': now,
        'updated_at': now
    }

    follows.append(new_follow)
    _save_user_follows(follows)

    status = "accepted" if new_follow['status'] == 'accepted' else "pending"
    message = f"{'Connected with' if status == 'accepted' else 'Connection request sent to'} {target_user['name']}"

    return ConnectionResponse(success=True, message=message, status=status)

@router.delete("/users/{user_id}/disconnect")
@api_rate_limit("social_operations")
@require_authenticated
async def disconnect_user(
    user_id: str,
    request: Request
):
    """Remove a connection or pending request."""
    current_user_id = get_current_user_id(request)

    follows = _load_user_follows()

    # Find and remove the follow relationship
    follow_to_remove = next((f for f in follows if (
        (f['follower_id'] == current_user_id and f['following_id'] == user_id) or
        (f['follower_id'] == user_id and f['following_id'] == current_user_id)
    )), None)

    if not follow_to_remove:
        raise HTTPException(status_code=400, detail="Not following this user")

    follows.remove(follow_to_remove)
    _save_user_follows(follows)

    return {"message": "Connection removed"}

@router.get("/connection-requests", response_model=List[ConnectionRequestItem])
@api_rate_limit("social_operations")
@require_authenticated
async def get_follow_requests(
    request: Request
):
    """Get pending connection requests for current user"""
    current_user_id = get_current_user_id(request)

    follows = _load_user_follows()
    users = _load_users()

    # Get pending requests where current user is being followed
    pending_requests = [f for f in follows if f['following_id'] == current_user_id and f['status'] == 'pending']

    result = []
    for req in pending_requests:
        follower = next((u for u in users if u['id'] == req['follower_id']), None)
        if follower:
            result.append(ConnectionRequestItem(
                id=req['id'],
                requester=_build_profile_response(follower),
                created_at=req['created_at']
            ))

    return result

@router.post("/connection-requests/{request_id}/accept")
@api_rate_limit("social_operations")
@require_authenticated
async def accept_follow_request(
    request_id: str,
    request: Request
):
    """Accept a connection request"""
    current_user_id = get_current_user_id(request)

    follows = _load_user_follows()

    # Find the request
    follow_req = next((f for f in follows if f['id'] == request_id), None)
    if not follow_req:
        raise HTTPException(status_code=404, detail="Follow request not found")

    # Check if current user is the target
    if follow_req['following_id'] != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to accept this request")

    if follow_req['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")

    # Accept the request
    follow_req['status'] = 'accepted'
    follow_req['updated_at'] = _now_ist()
    _save_user_follows(follows)

    return {"message": "Connection request accepted"}

@router.post("/connection-requests/{request_id}/decline")
@api_rate_limit("social_operations")
@require_authenticated
async def decline_follow_request(
    request_id: str,
    request: Request
):
    """Decline a connection request"""
    current_user_id = get_current_user_id(request)

    follows = _load_user_follows()

    # Find the request
    follow_req = next((f for f in follows if f['id'] == request_id), None)
    if not follow_req:
        raise HTTPException(status_code=404, detail="Follow request not found")

    # Check if current user is the target
    if follow_req['following_id'] != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to decline this request")

    # Remove the request
    follows.remove(follow_req)
    _save_user_follows(follows)

    return {"message": "Connection request declined"}

@router.get("/users/{user_id}/connections")
@api_rate_limit("social_operations")
@require_authenticated
async def get_user_connections(
    user_id: str,
    request: Request
):
    """Get user's connections (accepted, either direction)."""
    current_user_id = get_current_user_id(request)

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()

    # Check if current user can view followers
    if not _can_view_profile(current_user_id, user, follows):
        raise HTTPException(status_code=403, detail="Cannot view connections of private account")

    # Collect accepted connections (both directions)
    connection_user_ids = set()
    for f in follows:
        if f['status'] != 'accepted':
            continue
        if f['following_id'] == user_id:
            connection_user_ids.add(f['follower_id'])
        if f['follower_id'] == user_id:
            connection_user_ids.add(f['following_id'])

    connections = []
    for cid in connection_user_ids:
        cu = next((u for u in users if u['id'] == cid), None)
        if cu:
            connections.append(_build_profile_response(cu, current_user_id, follows))

    return {"connections": connections, "count": len(connections)}

@router.get("/connections")
@api_rate_limit("social_operations")
@require_authenticated
async def get_my_connections(
    request: Request
):
    """Get current user's connections (accepted, either direction)."""
    current_user_id = get_current_user_id(request)

    users = _load_users()
    follows = _load_user_follows()

    # Collect accepted connections (both directions) for current user
    connection_user_ids = set()
    for f in follows:
        if f['status'] != 'accepted':
            continue
        if f['following_id'] == current_user_id:
            connection_user_ids.add(f['follower_id'])
        if f['follower_id'] == current_user_id:
            connection_user_ids.add(f['following_id'])

    connections = []
    for cid in connection_user_ids:
        cu = next((u for u in users if u['id'] == cid), None)
        if cu:
            connections.append(_build_profile_response(cu, current_user_id, follows))

    return {"connections": connections, "count": len(connections)}

@router.get("/feed")
@api_rate_limit("social_operations")
@require_authenticated
async def get_activity_feed(
    request: Request,
    limit: int = 20
):
    """Get activity feed from followed users"""
    current_user_id = get_current_user_id(request)

    follows = _load_user_follows()
    events = read_events()
    tickets = read_tickets()

    # Get users connected to current user
    following_ids = set()
    for f in follows:
        if f['status'] != 'accepted':
            continue
        if f['follower_id'] == current_user_id:
            following_ids.add(f['following_id'])
        if f['following_id'] == current_user_id:
            following_ids.add(f['follower_id'])

    # Get events attended by followed users
    followed_events = []
    for ticket in tickets:
        if ticket['userId'] in following_ids:
            event = next((e for e in events if e['id'] == ticket['eventId']), None)
            if event:
                followed_events.append({
                    'event': event,
                    'user_id': ticket['userId'],
                    'attended_at': ticket['issuedAt']
                })

    # Sort by attendance time (most recent first)
    followed_events.sort(key=lambda x: x['attended_at'], reverse=True)

    return {
        "activities": followed_events[:limit],
        "total": len(followed_events)
    }

# Admin messaging endpoints (no-op if WhatsApp not configured)
@router.post("/admin/notify/all")
@require_role(UserRole.ADMIN)
async def admin_notify_all_users(message: str):
    users = _load_users()
    phones = [u.get("phone") for u in users if u.get("phone")]
    if not phones:
        return {"sent": 0, "message": "No users with phone numbers"}
    results = await send_bulk_text(phones, message)
    sent = sum(1 for ok in results.values() if ok)
    return {"sent": sent, "total": len(phones)}

@router.post("/admin/notify/event/{event_id}")
@require_role(UserRole.ADMIN)
async def admin_notify_event_subscribers(event_id: str, message: str):
    users = _load_users()
    phones = [
        u.get("phone")
        for u in users
        if u.get("phone") and event_id in (u.get("subscribedEvents") or [])
    ]
    if not phones:
        return {"sent": 0, "message": "No subscribers with phone numbers"}
    results = await send_bulk_text(phones, message)
    sent = sum(1 for ok in results.values() if ok)
    return {"sent": sent, "total": len(phones)}

@router.get("/users/search")
@api_rate_limit("social_operations")
@require_authenticated
async def search_users(
    q: str,
    request: Request,
    limit: int = 10
):
    """Search users by name"""
    current_user_id = get_current_user_id(request)

    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

    # Sanitize search query
    sanitized_query = sql_protection.sanitize_string(q.strip())
    if not sanitized_query or len(sanitized_query) < 2:
        raise HTTPException(status_code=400, detail="Invalid search query")

    users = _load_users()
    follows = _load_user_follows()

    # Search users by name (case insensitive)
    query = sanitized_query.lower()
    matching_users = [
        u for u in users
        if query in u['name'].lower() and u['id'] != current_user_id
    ][:limit]

    # Build profile responses
    results = []
    for user in matching_users:
        results.append(_build_profile_response(user, current_user_id, follows))

    return {"users": results, "count": len(results)}
