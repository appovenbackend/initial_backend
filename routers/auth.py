from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Header
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from core.security import hash_password, verify_password, create_access_token
from core.rate_limiting import auth_rate_limit, api_rate_limit
from core.jwt_security import jwt_security_manager
from core.rbac import require_authenticated, get_current_user_id
from models.validation import SecureUserRegister, SecureUserLogin, SecureUserUpdate
from models.user import User
from utils.security import sql_protection, input_validator
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os
import shutil
from pathlib import Path
from jose import jwt

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

@router.post("/register")
@auth_rate_limit("register")
async def register(user_register: SecureUserRegister, request: Request):
    try:
        users = _load_users()

        # Check if phone number already exists
        existing_phone = next((u for u in users if u["phone"] == user_register.phone), None)
        if existing_phone:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "PHONE_ALREADY_REGISTERED",
                    "message": "Phone number already registered.",
                    "code": "AUTH_005",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Check if email already exists
        existing_email = next((u for u in users if u.get("email") == user_register.email), None)
        if existing_email:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "EMAIL_ALREADY_REGISTERED",
                    "message": "Email already registered.",
                    "code": "AUTH_006",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Create new user with hashed password
        hashed_password = hash_password(user_register.password)
        new_user = User(
            id="u_" + uuid4().hex[:10],
            name=user_register.name,
            phone=user_register.phone,
            email=user_register.email,
            password=hashed_password,
            role="user",
            createdAt=datetime.now(IST).isoformat()
        ).dict()
        users.append(new_user)
        _save_users(users)

        # Create access token using enhanced JWT security
        access_token = jwt_security_manager.create_token(new_user["id"], {"role": new_user.get("role", "user")})

        return {
            "msg": "User registered successfully",
            "user": {
                "id": new_user["id"],
                "name": new_user["name"],
                "email": new_user["email"],
                "phone": new_user["phone"],
                "createdAt": new_user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "REGISTRATION_FAILED",
                "message": "Failed to complete user registration.",
                "code": "AUTH_004",
                "timestamp": datetime.now(IST).isoformat(),
                "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )

@router.post("/login")
@auth_rate_limit("login")
async def login(user_login: SecureUserLogin, request: Request):
    try:


        users = _load_users()

        # Find user by phone number
        user = next((u for u in users if u["phone"] == user_login.phone), None)
        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "USER_NOT_FOUND",
                    "message": "User not found. Please register first.",
                    "code": "AUTH_001",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Check if user has a password (registered users should have one)
        if not user.get("password"):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "USER_HAS_NO_PASSWORD",
                    "message": "User found but has no password. Please complete registration with password.",
                    "code": "AUTH_002",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Verify password
        if not verify_password(user_login.password, user["password"]):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "INVALID_PASSWORD",
                    "message": "Invalid password provided.",
                    "code": "AUTH_003",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Create access token using enhanced JWT security
        access_token = jwt_security_manager.create_token(user["id"], {"role": user.get("role", "user")})

        return {
            "msg": "login_successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user.get("email"),
                "phone": user["phone"],
                "bio": user.get("bio"),
                "strava_link": user.get("strava_link"),
                "instagram_id": user.get("instagram_id"),
                "picture": user.get("picture"),
                "role": user.get("role", "user"),
                "createdAt": user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Internal server error during login.",
                "code": "AUTH_999",
                "timestamp": datetime.now(IST).isoformat(),
                "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )

@router.get("/users")
#@api_rate_limit("admin")
async def get_all_users(request: Request):
    users = _load_users()
    return {"users": users}

@router.get("/user/{phone}")
async def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "error": "USER_NOT_FOUND",
                "message": "User not found.",
                "code": "AUTH_007",
                "timestamp": datetime.now(IST).isoformat()
            }
        )
    return user

@router.put("/user/{user_id}")
@api_rate_limit("authenticated")
@require_authenticated
async def update_user(
    user_id: str,
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    bio: str = Form(None),
    strava_link: str = Form(None),
    instagram_id: str = Form(None),
    picture: UploadFile = File(None),
    request: Request = None
):
    # Security check - users can only update their own profile
    current_user_id = get_current_user_id(request)
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Can only update your own profile")
    
    users = _load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Sanitize input data
    update_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "bio": bio,
        "strava_link": strava_link,
        "instagram_id": instagram_id
    }
    sanitized_data = sql_protection.validate_input(update_data)

    # Update only provided fields
    updated = False

    if sanitized_data["name"] is not None and sanitized_data["name"].strip():
        user["name"] = sanitized_data["name"].strip()
        updated = True

    if sanitized_data["phone"] is not None and sanitized_data["phone"].strip():
        new_phone = sanitized_data["phone"].strip()
        # Validate phone format
        if not input_validator.validate_phone_number(new_phone):
            raise HTTPException(status_code=400, detail="Invalid phone number format")
        # Check if phone number already exists for another user
        existing_phone_user = next((u for u in users if u["phone"] == new_phone and u["id"] != user_id), None)
        if existing_phone_user:
            raise HTTPException(status_code=400, detail="Phone number already exists for another user")
        user["phone"] = new_phone
        updated = True

    if sanitized_data["email"] is not None and sanitized_data["email"].strip():
        email = sanitized_data["email"].strip()
        # Validate email format
        if not input_validator.validate_email(email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        user["email"] = email
        updated = True

    if sanitized_data["bio"] is not None:
        user["bio"] = sanitized_data["bio"].strip() if sanitized_data["bio"].strip() else None
        updated = True

    if sanitized_data["strava_link"] is not None:
        strava_link = sanitized_data["strava_link"].strip() if sanitized_data["strava_link"].strip() else None
        if strava_link and not input_validator.validate_url(strava_link):
            raise HTTPException(status_code=400, detail="Invalid Strava link format")
        user["strava_link"] = strava_link
        updated = True

    if sanitized_data["instagram_id"] is not None:
        user["instagram_id"] = sanitized_data["instagram_id"].strip() if sanitized_data["instagram_id"].strip() else None
        updated = True

    if picture is not None:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/profiles")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename with security validation
        file_extension = Path(picture.filename).suffix
        sanitized_filename = input_validator.sanitize_filename(picture.filename)
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

@router.get("/password")
async def return_password():
    return "yesmakeedits"

# Google OAuth routes
@router.get("/google_login")
@auth_rate_limit("google_auth")
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
            access_token = jwt_security_manager.create_token(existing_user["id"], {"role": existing_user.get("role", "user")})
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
                    "role": existing_user.get("role", "user"),
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
        access_token = jwt_security_manager.create_token(new_user["id"], {"role": "user"})
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
                "role": new_user.get("role", "user"),
                "createdAt": new_user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")

@router.get("/points")
@api_rate_limit("authenticated")
@require_authenticated
async def get_user_points(request: Request):
    """Get user points for display"""
    from utils.database import get_user_points

    current_user_id = get_current_user_id(request)
    points_data = get_user_points(current_user_id)

    # Return user-friendly format
    return {
        "user_id": points_data["id"],
        "total_points": points_data["total_points"],
        "point_history": points_data["transaction_history"]
    }
