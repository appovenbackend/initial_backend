from pydantic import BaseModel
from typing import Optional

class CreateEventIn(BaseModel):
    title: str
    description: str
    city: str
    venue: str
    startAt: str
    endAt: str
    priceINR: int
    bannerUrl: Optional[str] = None
    isActive: Optional[bool] = True

class Event(BaseModel):
    id: str
    title: str
    description: str
    city: str
    venue: str
    startAt: str
    endAt: str
    priceINR: int
    bannerUrl: Optional[str] = None
    isActive: bool = True
    createdAt: str
