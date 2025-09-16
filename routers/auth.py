from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from utils.filedb import read_json, write_json
from core.config import USERS_FILE
from models.user import UserIn, User
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/auth", tags=["Auth"])

def _load_users():
    return read_json(USERS_FILE)

def _save_users(data):
    write_json(USERS_FILE, data)

@router.post("/register")
def register(user_in: UserIn):
    users = _load_users()
    if any(u["phone"] == user_in.phone for u in users):
        raise HTTPException(status_code=400, detail="Phone already registered")
    new_user = User(
        id="u_" + uuid4().hex[:10],
        name=user_in.name,
        phone=user_in.phone,
        role="user",
        createdAt=datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    ).dict()
    users.append(new_user)
    _save_users(users)
    return {"msg": "registered", "userId": new_user["id"]}

@router.get("/user/{phone}")
def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
