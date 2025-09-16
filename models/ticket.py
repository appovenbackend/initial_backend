from pydantic import BaseModel
from typing import Optional, List, Dict

class ValidationEntry(BaseModel):
    ts: str
    device: Optional[str] = None
    operator: Optional[str] = None

class Ticket(BaseModel):
    id: str
    eventId: str
    userId: str
    qrToken: str
    issuedAt: str
    isValidated: bool = False
    validatedAt: Optional[str] = None
    validationHistory: Optional[List[Dict]] = []
    meta: Optional[Dict] = {}
