import os, random, logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import OTP

log = logging.getLogger(__name__)

SENDER_MODE = os.getenv("OTP_SENDER", "console")
OTP_TTL = int(os.getenv("OTP_TTL_SECONDS", "300"))

def generate_code() -> str:
    return f"{random.randint(100000, 999999)}"

def send_otp(db: Session, phone: str) -> None:
    code = generate_code()
    expires = datetime.utcnow() + timedelta(seconds=OTP_TTL)
    db.add(OTP(phone=phone, code=code, expires_at=expires))
    db.commit()
    if SENDER_MODE == "console":
        log.warning(f"[OTP] {phone} -> {code} (expire {OTP_TTL}s)")
