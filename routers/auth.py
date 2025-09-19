from fastapi import APIRouter, HTTPException, Request
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from models.user import UserIn, User
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os
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
def login(user_in: UserIn):
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

@router.get("/user/{phone}")
def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Google OAuth routes
@router.get("/google_login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google_login/callback")
async def google_callback(request: Request):
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
            "createdAt": new_user["createdAt"]
        },
        "access_token": access_token,
        "token_type": "bearer"
    }
