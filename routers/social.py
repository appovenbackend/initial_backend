from fastapi import APIRouter, HTTPException, Depends, Request
from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from models.user_follow import (
    UserFollow, FollowRequest, FollowResponse,
    UserProfileResponse, FollowRequestItem
)
from models.user import User
from utils.database import (
    read_users, write_users, read_user_follows, write_user_follows,
    read_events, read_tickets
)
from core.config import IST
import json

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

def get_current_user(request: Request) -> str:
    """Extract user ID from JWT token (simplified for now)"""
    # In a real app, you'd decode the JWT token from Authorization header
    # For now, we'll assume user_id is passed in a custom header for testing
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    return user_id

def _get_relationship_status(current_user_id: str, target_user_id: str, follows: list) -> dict:
    """Get relationship status between two users"""
    # Check if current user is following target user
    following_relationship = next(
        (f for f in follows
         if f['follower_id'] == current_user_id and f['following_id'] == target_user_id),
        None
    )

    # Check if target user is following current user
    followed_by_relationship = next(
        (f for f in follows
         if f['follower_id'] == target_user_id and f['following_id'] == current_user_id),
        None
    )

    return {
        'is_following': following_relationship is not None,
        'is_followed_by': followed_by_relationship is not None,
        'follow_status': following_relationship['status'] if following_relationship else None
    }

def _can_view_profile(viewer_id: str, target_user: dict, follows: list) -> bool:
    """Check if viewer can see target's full profile"""
    if not target_user.get('is_private', False):
        return True  # Public profile

    # Check if viewer is following the target user and it's accepted
    relationship = next(
        (f for f in follows
         if f['follower_id'] == viewer_id and f['following_id'] == target_user['id']),
        None
    )

    return relationship is not None and relationship['status'] == 'accepted'

def _build_profile_response(user: dict, viewer_id: str = None, follows: list = None) -> UserProfileResponse:
    """Build profile response with privacy controls"""
    if not follows:
        follows = []

    # Get follower/following counts
    follower_count = len([f for f in follows if f['following_id'] == user['id'] and f['status'] == 'accepted'])
    following_count = len([f for f in follows if f['follower_id'] == user['id'] and f['status'] == 'accepted'])

    # Base response
    response = UserProfileResponse(
        id=user['id'],
        name=user['name'],
        picture=user.get('picture'),
        bio=user.get('bio'),
        is_private=user.get('is_private', False),
        follower_count=follower_count,
        following_count=following_count,
        created_at=user['createdAt']
    )

    # Add relationship status if viewer is specified
    if viewer_id:
        relationship = _get_relationship_status(viewer_id, user['id'], follows)
        response.is_following = relationship['is_following']
        response.is_followed_by = relationship['is_followed_by']
        response.follow_status = relationship['follow_status']

        # Add private info only if viewer can see it
        if _can_view_profile(viewer_id, user, follows):
            response.phone = user.get('phone')
            response.email = user.get('email')
            response.strava_link = user.get('strava_link')
            response.instagram_id = user.get('instagram_id')
            response.subscribed_events = user.get('subscribedEvents', [])

    return response

@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str, request: Request):
    """Get user profile with privacy controls"""
    current_user_id = get_current_user(request)

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()
    return _build_profile_response(user, current_user_id, follows)

@router.put("/users/{user_id}/privacy")
async def update_privacy_setting(user_id: str, is_private: bool, request: Request):
    """Toggle account privacy setting"""
    current_user_id = get_current_user(request)

    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Can only update your own privacy settings")

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user['is_private'] = is_private
    _save_users(users)

    return {"message": f"Account set to {'private' if is_private else 'public'}", "is_private": is_private}

@router.post("/users/{user_id}/follow", response_model=FollowResponse)
async def follow_user(user_id: str, request: Request):
    """Follow a user or send follow request"""
    current_user_id = get_current_user(request)

    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    users = _load_users()
    target_user = next((u for u in users if u['id'] == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()

    # Check if already following
    existing_follow = next(
        (f for f in follows
         if f['follower_id'] == current_user_id and f['following_id'] == user_id),
        None
    )

    if existing_follow:
        if existing_follow['status'] == 'accepted':
            raise HTTPException(status_code=400, detail="Already following this user")
        elif existing_follow['status'] == 'pending':
            raise HTTPException(status_code=400, detail="Follow request already pending")

    # Create follow relationship
    now = _now_ist()
    new_follow = {
        'id': f"follow_{uuid4().hex[:10]}",
        'follower_id': current_user_id,
        'following_id': user_id,
        'status': 'accepted' if not target_user.get('is_private', False) else 'pending',
        'created_at': now,
        'updated_at': now
    }

    follows.append(new_follow)
    _save_user_follows(follows)

    status = "following" if new_follow['status'] == 'accepted' else "pending"
    message = f"{'Following' if status == 'following' else 'Follow request sent to'} {target_user['name']}"

    return FollowResponse(success=True, message=message, status=status)

@router.delete("/users/{user_id}/unfollow")
async def unfollow_user(user_id: str, request: Request):
    """Unfollow a user"""
    current_user_id = get_current_user(request)

    follows = _load_user_follows()

    # Find and remove the follow relationship
    follow_to_remove = next(
        (f for f in follows
         if f['follower_id'] == current_user_id and f['following_id'] == user_id),
        None
    )

    if not follow_to_remove:
        raise HTTPException(status_code=400, detail="Not following this user")

    follows.remove(follow_to_remove)
    _save_user_follows(follows)

    return {"message": "Successfully unfollowed user"}

@router.get("/follow-requests", response_model=List[FollowRequestItem])
async def get_follow_requests(request: Request):
    """Get pending follow requests for current user"""
    current_user_id = get_current_user(request)

    follows = _load_user_follows()
    users = _load_users()

    # Get pending requests where current user is being followed
    pending_requests = [
        f for f in follows
        if f['following_id'] == current_user_id and f['status'] == 'pending'
    ]

    result = []
    for req in pending_requests:
        follower = next((u for u in users if u['id'] == req['follower_id']), None)
        if follower:
            result.append(FollowRequestItem(
                id=req['id'],
                follower=_build_profile_response(follower),
                created_at=req['created_at']
            ))

    return result

@router.post("/follow-requests/{request_id}/accept")
async def accept_follow_request(request_id: str, request: Request):
    """Accept a follow request"""
    current_user_id = get_current_user(request)

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

    return {"message": "Follow request accepted"}

@router.post("/follow-requests/{request_id}/decline")
async def decline_follow_request(request_id: str, request: Request):
    """Decline a follow request"""
    current_user_id = get_current_user(request)

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

    return {"message": "Follow request declined"}

@router.get("/users/{user_id}/followers")
async def get_user_followers(user_id: str, request: Request):
    """Get user's followers"""
    current_user_id = get_current_user(request)

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()

    # Check if current user can view followers
    if not _can_view_profile(current_user_id, user, follows):
        raise HTTPException(status_code=403, detail="Cannot view followers of private account")

    # Get accepted followers
    follower_ids = [
        f['follower_id'] for f in follows
        if f['following_id'] == user_id and f['status'] == 'accepted'
    ]

    followers = []
    for follower_id in follower_ids:
        follower = next((u for u in users if u['id'] == follower_id), None)
        if follower:
            followers.append(_build_profile_response(follower, current_user_id, follows))

    return {"followers": followers, "count": len(followers)}

@router.get("/users/{user_id}/following")
async def get_user_following(user_id: str, request: Request):
    """Get users that this user is following"""
    current_user_id = get_current_user(request)

    users = _load_users()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    follows = _load_user_follows()

    # Check if current user can view following
    if not _can_view_profile(current_user_id, user, follows):
        raise HTTPException(status_code=403, detail="Cannot view following of private account")

    # Get accepted following
    following_ids = [
        f['following_id'] for f in follows
        if f['follower_id'] == user_id and f['status'] == 'accepted'
    ]

    following = []
    for following_id in following_ids:
        followed_user = next((u for u in users if u['id'] == following_id), None)
        if followed_user:
            following.append(_build_profile_response(followed_user, current_user_id, follows))

    return {"following": following, "count": len(following)}

@router.get("/feed")
async def get_activity_feed(request: Request, limit: int = 20):
    """Get activity feed from followed users"""
    current_user_id = get_current_user(request)

    follows = _load_user_follows()
    events = read_events()
    tickets = read_tickets()

    # Get users that current user follows
    following_ids = [
        f['following_id'] for f in follows
        if f['follower_id'] == current_user_id and f['status'] == 'accepted'
    ]

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

@router.get("/users/search")
async def search_users(q: str, request: Request, limit: int = 10):
    """Search users by name"""
    current_user_id = get_current_user(request)

    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")

    users = _load_users()
    follows = _load_user_follows()

    # Search users by name (case insensitive)
    query = q.strip().lower()
    matching_users = [
        u for u in users
        if query in u['name'].lower() and u['id'] != current_user_id
    ][:limit]

    # Build profile responses
    results = []
    for user in matching_users:
        results.append(_build_profile_response(user, current_user_id, follows))

    return {"users": results, "count": len(results)}
