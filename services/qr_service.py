from datetime import datetime, timezone
from jose import jwt
from core.config import SECRET_KEY, ALGORITHM, QR_DEFAULT_TTL_SECONDS, IST
from dateutil import parser

def _ist_to_utc_ts(iso_str: str) -> int:
    dt = parser.isoparse(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    # convert to UTC ts
    return int(dt.astimezone(timezone.utc).timestamp())

def create_qr_token(ticket_id: str, user_id: str, event_id: str, event_end_iso_ist: str | None = None) -> str:
    now = datetime.now(IST)
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
