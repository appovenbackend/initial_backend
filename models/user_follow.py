from pydantic import BaseModel
from typing import Optional

class UserFollow(BaseModel):
    id: str
    follower_id: str  # User who is following
    following_id: str  # User being followed
    status: str  # 'pending', 'accepted', 'blocked'
    created_at: str
    updated_at: str

class FollowRequest(BaseModel):
    follower_id: str
    following_id: str

class FollowResponse(BaseModel):
    success: bool
    message: str
    status: Optional[str] = None  # 'following', 'pending', 'accepted'

class UserProfileResponse(BaseModel):
    id: str
    name: str
    picture: Optional[str] = None
    bio: Optional[str] = None
    is_private: bool = False
    follower_count: int = 0
    following_count: int = 0
    # Only show these for followers/friends
    phone: Optional[str] = None
    email: Optional[str] = None
    strava_link: Optional[str] = None
    instagram_id: Optional[str] = None
    subscribed_events: Optional[list] = None
    created_at: str
    # Relationship status
    is_following: bool = False
    is_followed_by: bool = False
    follow_status: Optional[str] = None  # 'pending', 'accepted', 'blocked'

class FollowRequestItem(BaseModel):
    id: str
    follower: UserProfileResponse
    created_at: str
