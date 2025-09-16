from pydantic import BaseModel
from typing import Optional

class UserIn(BaseModel):
    name: str
    phone: str
    password: str

class User(BaseModel):
    id: str
    name: str
    phone: str
    hashed_password: str
    role: Optional[str] = "user"
    createdAt: str
