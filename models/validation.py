"""
Enhanced Input Validation with Security
"""
from pydantic import BaseModel, validator, Field
from typing import Optional, List
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SecureEventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9\s\-_.,!?]+$')
    description: str = Field(..., min_length=10, max_length=2000)
    city: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-zA-Z\s]+$')
    venue: str = Field(..., min_length=3, max_length=100)
    startAt: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    endAt: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    priceINR: int = Field(..., ge=0, le=100000)  # 0 to 1 lakh
    bannerUrl: Optional[str] = Field(None, pattern=r'^https?://.+\.(jpg|jpeg|png|gif|webp)$')
    isActive: Optional[bool] = True
    organizerName: Optional[str] = Field("bhag", max_length=50)
    organizerLogo: Optional[str] = Field("https://example.com/default-logo.png", pattern=r'^https?://.+\.(jpg|jpeg|png|gif|webp)$')
    coordinate_lat: Optional[str] = Field(None, pattern=r'^-?\d+\.?\d*$')
    coordinate_long: Optional[str] = Field(None, pattern=r'^-?\d+\.?\d*$')
    address_url: Optional[str] = Field(None, pattern=r'^https?://.+')
    registration_link: Optional[str] = Field(None, pattern=r'^https?://.+')
    requires_approval: Optional[bool] = False
    registration_open: Optional[bool] = True
    
    @validator('endAt')
    def validate_end_after_start(cls, v, values):
        if 'startAt' in values:
            try:
                start = datetime.fromisoformat(values['startAt'])
                end = datetime.fromisoformat(v)
                if end <= start:
                    raise ValueError('End time must be after start time')
            except ValueError as e:
                if "End time must be after start time" in str(e):
                    raise e
                # If datetime parsing fails, let Pydantic handle it
                pass
        return v

class SecureUserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50, pattern=r'^[a-zA-Z\s]+$')
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')  # E.164 format
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    bio: Optional[str] = Field(None, max_length=500)
    strava_link: Optional[str] = Field(None, pattern=r'^https://www\.strava\.com/athletes/\d+/?$')
    instagram_id: Optional[str] = Field(None, pattern=r'^@?[a-zA-Z0-9._]{1,30}$')

class SecureUserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-zA-Z\s]+$')
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8, max_length=128)

class SecureUserLogin(BaseModel):
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    password: str = Field(..., min_length=1, max_length=128)

class SecurePaymentRequest(BaseModel):
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    eventId: str = Field(..., pattern=r'^evt_[a-f0-9]{10}$')
    razorpay_order_id: Optional[str] = Field(None, pattern=r'^order_[a-zA-Z0-9]+$')
    razorpay_payment_id: Optional[str] = Field(None, pattern=r'^pay_[a-zA-Z0-9]+$')
    razorpay_signature: Optional[str] = Field(None, pattern=r'^[a-f0-9]{64}$')

class SecureTicketValidation(BaseModel):
    token: str = Field(..., min_length=10, max_length=1000)
    eventId: str = Field(..., pattern=r'^evt_[a-f0-9]{10}$')

class SecureEventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9\s\-_.,!?]+$')
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    city: Optional[str] = Field(None, min_length=2, max_length=50, pattern=r'^[a-zA-Z\s]+$')
    venue: Optional[str] = Field(None, min_length=3, max_length=100)
    startAt: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')
    endAt: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')
    priceINR: Optional[int] = Field(None, ge=0, le=100000)
    bannerUrl: Optional[str] = Field(None, pattern=r'^https?://.+\.(jpg|jpeg|png|gif|webp)$')
    isActive: Optional[bool] = None
    organizerName: Optional[str] = Field(None, max_length=50)
    organizerLogo: Optional[str] = Field(None, pattern=r'^https?://.+\.(jpg|jpeg|png|gif|webp)$')
    coordinate_lat: Optional[str] = Field(None, pattern=r'^-?\d+\.?\d*$')
    coordinate_long: Optional[str] = Field(None, pattern=r'^-?\d+\.?\d*$')
    address_url: Optional[str] = Field(None, pattern=r'^https?://.+')
    registration_link: Optional[str] = Field(None, pattern=r'^https?://.+')
    requires_approval: Optional[bool] = None
    registration_open: Optional[bool] = None

class SecureFreeRegistration(BaseModel):
    phone: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    eventId: str = Field(..., pattern=r'^evt_[a-f0-9]{10}$')
