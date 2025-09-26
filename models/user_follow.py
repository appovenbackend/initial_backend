from pydantic import BaseModel
from typing import Optional


class UserConnection(BaseModel):
    id: str
    follower_id: str  # requester (kept for DB compatibility)
    following_id: str  # target (kept for DB compatibility)
    status: str  # 'pending', 'accepted', 'blocked'
    created_at: str
    updated_at: str


class ConnectionRequest(BaseModel):
    requester_id: str
    target_id: str


class ConnectionResponse(BaseModel):
    success: bool
    message: str
    status: Optional[str] = None  # 'pending', 'accepted'


class UserProfileResponse(BaseModel):
    id: str
    name: str
    picture: Optional[str] = None
    bio: Optional[str] = None
    is_private: bool = False
    connections_count: int = 0
    # Only show these for connected users
    phone: Optional[str] = None
    email: Optional[str] = None
    strava_link: Optional[str] = None
    instagram_id: Optional[str] = None
    subscribed_events: Optional[list] = None
    created_at: str
    # Relationship status
    is_connected: bool = False
    connection_status: Optional[str] = None  # 'pending', 'accepted'


class ConnectionRequestItem(BaseModel):
    id: str
    requester: UserProfileResponse
    created_at: str
