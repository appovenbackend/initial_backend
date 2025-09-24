from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from models.user import UserIn, User, UserUpdate
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

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/login")
async def login(user_in: UserIn):
    try:
        users = _load_users()

        # Check if user already exists with this phone number
        existing_user = next((u for u in users if u["phone"] == user_in.phone), None)

        if existing_user:
            # User exists, return existing user info
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

        # User doesn't exist, create new user
        new_user = User(
            id="u_" + uuid4().hex[:10],
            name=user_in.name,
            phone=user_in.phone,
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
