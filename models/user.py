from pydantic import BaseModel
from typing import Optional, List

class UserIn(BaseModel):
    name: str
    phone: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    strava_link: Optional[str] = None
    instagram_id: Optional[str] = None
    picture: Optional[str] = None
    

class User(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None
    google_id: Optional[str] = None
    role: str = "user"
    bio: Optional[str] = None
    strava_link: Optional[str] = None
    instagram_id: Optional[str] = None
    subscribedEvents: List[str] = []
    is_private: bool = False
    createdAt: str
