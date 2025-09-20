from pydantic import BaseModel
from typing import Optional

class UserIn(BaseModel):
    name: str
    phone: str

class UserUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None

class User(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None
    google_id: Optional[str] = None
    role: str = "user"
    createdAt: str
