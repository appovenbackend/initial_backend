import os
import qrcode
from datetime import datetime, timezone
from jose import jwt
from core.config import DATA_DIR, SECRET_KEY, ALGORITHM, QR_DEFAULT_TTL_SECONDS
from dateutil import parser
from zoneinfo import ZoneInfo

QR_DIR = os.path.join(DATA_DIR, "qrs")
os.makedirs(QR_DIR, exist_ok=True)

def _ist_to_utc_ts(iso_str: str) -> int:
    # parse ISO in IST (user to give ISO but we treat it as IST)
    # allow ISO with timezone; if naive, treat as IST
    dt = parser.isoparse(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    # convert to UTC ts
    return int(dt.astimezone(timezone.utc).timestamp())

def create_qr_token(ticket_id: str, user_id: str, event_id: str, event_end_iso_ist: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    if event_end_iso_ist:
        exp_ts = _ist_to_utc_ts(event_end_iso_ist)
    else:
        exp_ts = int((now.timestamp() + QR_DEFAULT_TTL_SECONDS))
    payload = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "event_id": event_id,
        "iat": int(now.timestamp()),
        "exp": int(exp_ts)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def generate_qr_image(token: str, ticket_id: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(QR_DIR, f"{ticket_id}.png")
    img.save(path)
    return path
