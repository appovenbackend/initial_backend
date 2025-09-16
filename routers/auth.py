from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from utils.filedb import read_json, write_json
from core.config import USERS_FILE, IST
from models.user import UserIn, User

router = APIRouter(prefix="/auth", tags=["Auth"])

def _load_users():
    return read_json(USERS_FILE)

def _save_users(data):
    write_json(USERS_FILE, data)

@router.post("/login")
def login(user_in: UserIn):
    users = _load_users()

    # Check if user already exists with this phone number
    existing_user = next((u for u in users if u["phone"] == user_in.phone), None)

    if existing_user:
        # User exists, return existing user info
        return {
            "msg": "login_successful",
            "userId": existing_user["id"],
            "name": existing_user["name"],
            "phone": existing_user["phone"],
            "createdAt": existing_user["createdAt"]
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
    return {
        "msg": "registered",
        "userId": new_user["id"],
        "name": new_user["name"],
        "phone": new_user["phone"],
        "createdAt": new_user["createdAt"]
    }

@router.get("/user/{phone}")
def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
