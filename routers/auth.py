from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Header
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from core.security import hash_password, verify_password, create_access_token
from models.user import UserIn, User, UserUpdate, UserRegister, UserLogin
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
async def register(user_register: UserRegister):
    try:
        users = _load_users()

        # Check if phone number already exists
        existing_phone = next((u for u in users if u["phone"] == user_register.phone), None)
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone number already registered")

        # Check if email already exists
        existing_email = next((u for u in users if u.get("email") == user_register.email), None)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

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

        # Create access token
        access_token = create_access_token(subject=new_user["id"])

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
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
async def login(user_login: UserLogin):
    try:
        users = _load_users()

        # Find user by phone number
        user = next((u for u in users if u["phone"] == user_login.phone), None)
        if not user:
            raise HTTPException(status_code=401, detail="User not found. Please register first.")

        # Check if user has a password (registered users should have one)
        if not user.get("password"):
            raise HTTPException(status_code=401, detail="User not found. Please register first.")

        # Verify password
        if not verify_password(user_login.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid password")

        # Create access token
        access_token = create_access_token(subject=user["id"])

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
                "createdAt": user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

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

@router.get("/password")
async def return_password():
    return "yesmakeedits"

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
            access_token = create_access_token(subject=existing_user["id"])
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
        access_token = create_access_token(subject=new_user["id"])
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

