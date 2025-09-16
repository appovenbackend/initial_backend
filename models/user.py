from pydantic import BaseModel
from typing import Optional

class UserIn(BaseModel):
    name: str
    phone: str

class User(BaseModel):
    id: str
    name: str
    phone: str
    role: Optional[str] = "user"
    createdAt: str
