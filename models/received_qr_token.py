from pydantic import BaseModel
from datetime import datetime

class ReceivedQrToken(BaseModel):
    id: str
    token: str
    receivedAt: str
