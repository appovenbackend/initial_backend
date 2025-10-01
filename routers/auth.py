from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Header
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from models.user import UserIn, User, UserUpdate, UserSignup, UserLogin, OtpRequest, OtpVerify, PasswordReset
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os
import shutil
from pathlib import Path
from jose import jwt
import random
from passlib.context import CryptContext
from services.whatsapp_service import send_whatsapp_text

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OTP Storage: {phone: {"otp": str, "purpose": str, "expiry": datetime}}
otp_store = {}

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def generate_otp():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_message(phone: str, otp: str, purpose: str):
    """Send OTP via WhatsApp with purpose-specific message."""
    messages = {
        "signup": f"Your signup verification code: {otp}. Valid for 5 minutes.",
        "login": f"Your login verification code: {otp}. Valid for 5 minutes.",
        "reset": f"Your password reset code: {otp}. Valid for 5 minutes."
    }
    message = messages.get(purpose, f"Your verification code: {otp}")
    phone_e164 = normalize_phone(phone)
    success = send_whatsapp_text(phone_e164, message)
    return success

def store_otp(phone: str, otp: str, purpose: str):
    """Store OTP with 5-minute expiry."""
    expiry = datetime.now(IST) + timedelta(minutes=5)
    otp_store[phone] = {
        "otp": otp,
        "purpose": purpose,
        "expiry": expiry
    }

def verify_otp(phone: str, otp: str, expected_purpose: str = None):
    """Verify OTP and return True if valid and matching purpose."""
    if phone not in otp_store:
        return False

    stored = otp_store[phone]
    if datetime.now(IST) > stored["expiry"]:
        # Delete expired
        del otp_store[phone]
        return False

    if stored["otp"] != otp:
        return False

    if expected_purpose and stored["purpose"] != expected_purpose:
        return False

    # OTP used, delete it
    del otp_store[phone]
    return True

# Clean up expired OTPs periodically (simple implementation)
def cleanup_expired_otps():
    now = datetime.now(IST)
    expired_phones = [phone for phone, data in otp_store.items() if now > data["expiry"]]
    for phone in expired_phones:
        del otp_store[phone]

def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format (+91xxxxxxxxx for India)."""
    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith('+'):
        return phone  # Already has country code
    elif phone.startswith('91') and len(phone) == 12:
        return '+' + phone
    elif len(phone) == 10:
        # Assume Indian 10-digit number
        return '+91' + phone
    else:
        # Assume already has country code without +
        return '+' + phone

router = APIRouter(prefix="/auth", tags=["Auth"])

# OAuth Config
config = Config(environ=os.environ)
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def _load_users():
    return read_users()

def _save_users(data):
    write_users(data)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/send-otp")
async def send_otp(request: OtpRequest):
    """Send OTP via WhatsApp for signup, login, or password reset."""
    cleanup_expired_otps()

    # Validate purpose
    if request.purpose not in ["signup", "login", "reset"]:
        raise HTTPException(status_code=400, detail="Invalid purpose. Must be 'signup', 'login', or 'reset'")

    # Normalize phone for lookups
    normalized_phone = normalize_phone(request.phone)

    # Check if phone already exists for signup
    if request.purpose == "signup":
        users = _load_users()
        existing_user = next((u for u in users if normalize_phone(u["phone"]) == normalized_phone), None)
        if existing_user:
            raise HTTPException(status_code=400, detail="Phone number already registered. Please login instead")

    # Check if phone exists for login/reset
    if request.purpose in ["login", "reset"]:
        users = _load_users()
        existing_user = next((u for u in users if normalize_phone(u["phone"]) == normalized_phone), None)
        if not existing_user:
            raise HTTPException(status_code=404, detail="No account found with this phone number")

    # Generate and store OTP
    otp = generate_otp()
    store_otp(request.phone, otp, request.purpose)

    # Send via WhatsApp
    success = await send_otp_message(request.phone, otp, request.purpose)
    if not success:
        del otp_store[request.phone]  # Remove if send failed
        raise HTTPException(status_code=500, detail="Failed to send OTP via WhatsApp")

    return {"message": "OTP sent successfully via WhatsApp"}

@router.post("/signup")
async def signup(user_data: UserSignup):
    """Signup with OTP verification."""
    cleanup_expired_otps()

    # Normalize phone number
    normalized_phone = normalize_phone(user_data.phone)

    # Verify OTP
    if not verify_otp(normalized_phone, user_data.otp, "signup"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Check if user already exists
    users = _load_users()
    existing_user = next((u for u in users if normalize_phone(u["phone"]) == normalized_phone), None)
    if existing_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Hash password if provided
    hashed_password = None
    if user_data.password:
        hashed_password = get_password_hash(user_data.password)

    # Create new user
    new_user = User(
        id="u_" + uuid4().hex[:10],
        name=user_data.name,
        phone=normalized_phone,
        password=hashed_password,
        role="user",
        createdAt=datetime.now(IST).isoformat()
    ).dict()

    users.append(new_user)
    _save_users(users)

    access_token = create_access_token(data={"sub": new_user["id"]})
    return {
        "msg": "registered",
        "userId": new_user["id"],
        "name": new_user["name"],
        "phone": new_user["phone"],
        "createdAt": new_user["createdAt"],
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/login")
async def login(user_data: UserLogin):
    """Login with password OR OTP depending on user state."""
    try:
        # Normalize phone for lookups
        normalized_phone = normalize_phone(user_data.phone)

        users = _load_users()
        existing_user = next((u for u in users if normalize_phone(u["phone"]) == normalized_phone), None)

        if not existing_user:
            raise HTTPException(status_code=404, detail="No account found with this phone number")

        # If user has password and provided password, verify password
        if existing_user.get("password") and user_data.password:
            if not verify_password(user_data.password, existing_user["password"]):
                raise HTTPException(status_code=401, detail="Invalid password")
        # If user has no password or provided OTP, verify OTP
        elif user_data.otp:
            cleanup_expired_otps()
            if not verify_otp(normalized_phone, user_data.otp, "login"):
                raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        else:
            raise HTTPException(status_code=400, detail="Password or OTP required for login")

        access_token = create_access_token(data={"sub": existing_user["id"]})
        return {
            "msg": "login_successful",
            "userId": existing_user["id"],
            "name": existing_user["name"],
            "phone": existing_user["phone"],
            "email": existing_user.get("email"),
            "bio": existing_user.get("bio"),
            "strava_link": existing_user.get("strava_link"),
            "instagram_id": existing_user.get("instagram_id"),
            "picture": existing_user.get("picture"),
            "createdAt": existing_user["createdAt"],
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/forgot-password")
async def forgot_password(request: OtpRequest):
    """Send OTP for password reset."""
    if request.purpose != "reset":
        raise HTTPException(status_code=400, detail="Purpose must be 'reset'")
    # Reuse send_otp logic
    return await send_otp(request)

@router.post("/reset-password")
async def reset_password(data: PasswordReset):
    """Reset password after OTP verification."""
    cleanup_expired_otps()

    # Normalize phone
    normalized_phone = normalize_phone(data.phone)

    # Verify OTP
    if not verify_otp(normalized_phone, data.otp, "reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Update user password
    users = _load_users()
    existing_user = next((u for u in users if normalize_phone(u["phone"]) == normalized_phone), None)
    if not existing_user:
        raise HTTPException(status_code=404, detail="No account found with this phone number")

    existing_user["password"] = get_password_hash(data.new_password)
    _save_users(users)

    return {"message": "Password reset successfully"}

@router.get("/users")
async def get_all_users():
    users = _load_users()
    return {"users": users}

@router.get("/user/{phone}")
async def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/user/{user_id}")
async def update_user(
    user_id: str,
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    bio: str = Form(None),
    strava_link: str = Form(None),
    instagram_id: str = Form(None),
    picture: UploadFile = File(None)
):
    users = _load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    updated = False

    if name is not None and name.strip():
        user["name"] = name.strip()
        updated = True

    if phone is not None and phone.strip():
        new_phone = phone.strip()
        # Check if phone number already exists for another user
        existing_phone_user = next((u for u in users if u["phone"] == new_phone and u["id"] != user_id), None)
        if existing_phone_user:
            raise HTTPException(status_code=400, detail="Phone number already exists for another user")
        user["phone"] = new_phone
        updated = True

    if email is not None and email.strip():
        user["email"] = email.strip()
        updated = True

    if bio is not None:
        user["bio"] = bio.strip() if bio.strip() else None
        updated = True

    if strava_link is not None:
        user["strava_link"] = strava_link.strip() if strava_link.strip() else None
        updated = True

    if instagram_id is not None:
        user["instagram_id"] = instagram_id.strip() if instagram_id.strip() else None
        updated = True

    if picture is not None:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/profiles")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_extension = Path(picture.filename).suffix
        unique_filename = f"{user_id}_{uuid4().hex[:8]}{file_extension}"
        file_path = upload_dir / unique_filename

        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(picture.file, buffer)

        # Store the relative path in user record
        user["picture"] = f"/uploads/profiles/{unique_filename}"
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Save updated users
    _save_users(users)
    return {"msg": "User updated successfully", "user": user}

# Google OAuth routes
@router.get("/google_login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google_login/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            raise HTTPException(status_code=400, detail="Google login failed")

        users = _load_users()
        # Check if user exists by email
        existing_user = next((u for u in users if u.get("email") == user_info["email"]), None)

        if existing_user:
            # User exists, return existing user info
            access_token = create_access_token(data={"sub": existing_user["id"]})
            return {
                "msg": "login_successful",
                "user": {
                    "id": existing_user["id"],
                    "name": existing_user["name"],
                    "email": existing_user.get("email"),
                    "picture": existing_user.get("picture"),
                    "phone": existing_user.get("phone"),
                    "bio": existing_user.get("bio"),
                    "strava_link": existing_user.get("strava_link"),
                    "instagram_id": existing_user.get("instagram_id"),
                    "createdAt": existing_user["createdAt"]
                },
                "access_token": access_token,
                "token_type": "bearer"
            }

        # User doesn't exist, create new user
        new_user = User(
            id="u_" + uuid4().hex[:10],
            name=user_info.get("name"),
            email=user_info["email"],
            picture=user_info.get("picture"),
            google_id=user_info.get("sub"),
            role="user",
            createdAt=datetime.now(IST).isoformat()
        ).dict()
        users.append(new_user)
        _save_users(users)
        access_token = create_access_token(data={"sub": new_user["id"]})
        return {
            "msg": "registered",
            "user": {
                "id": new_user["id"],
                "name": new_user["name"],
                "email": new_user["email"],
                "picture": new_user["picture"],
                "bio": new_user.get("bio"),
                "strava_link": new_user.get("strava_link"),
                "instagram_id": new_user.get("instagram_id"),
                "createdAt": new_user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")

@router.get("/points")
async def get_user_points(request: Request, x_user_id: str = Header(..., alias="X-User-ID", description="Current user ID for authentication")):
    """Get user points for display"""
    from utils.database import get_user_points

    points_data = get_user_points(x_user_id)

    # Return user-friendly format
    return {
        "user_id": points_data["id"],
        "total_points": points_data["total_points"],
        "point_history": points_data["transaction_history"]
    }
