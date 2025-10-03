import math
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

class UserSignup(BaseModel):
    phone: str
    name: str
    otp: str
    password: Optional[str] = None

class UserRegister(BaseModel):
    name: str
    phone: str
    email: str
    password: str

class UserLogin(BaseModel):
    phone: str
    password: str

class OtpRequest(BaseModel):
    phone: str
    purpose: str  # "signup", "login", "reset"

class OtpVerify(BaseModel):
    phone: str
    otp: str

class PasswordReset(BaseModel):
    phone: str
    otp: str
    new_password: str

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
    password: Optional[str] = None  # Hashed password
    createdAt: str


class UserPoints(BaseModel):
    """Legacy points tracking system"""
    id: str  # user_id
    total_points: int = 0
    transaction_history: List[dict] = []  # [{"type": "earned/spent", "points": int, "reason": str, "timestamp": str}]

    @staticmethod
    def calculate_points(event_price_inr: float) -> int:
        """Calculate points based on event type"""
        if event_price_inr <= 0:
            # Free event
            return 2
        else:
            # Paid event: ceil(price/100) + 2
            return math.ceil(event_price_inr / 100) + 2
