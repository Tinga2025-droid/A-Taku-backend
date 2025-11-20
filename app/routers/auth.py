# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db, Base, engine
from app.models import User, OTP
from app.schemas import OTPRequest, LoginRequest, TokenResponse
from app.otp_provider import send_otp
from app.auth import create_access_token, hash_password

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth", tags=["auth"])

DEFAULT_PIN = "0000"

def normalize_phone(p: str) -> str:
    p = p.strip().replace(" ", "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+"):
        if p.startswith(("84", "85", "86", "82")):
            p = "+258" + p
        elif p.startswith("258"):
            p = "+" + p
        else:
            p = "+" + p
    return p

@router.post("/otp")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        user = User(
            phone=phone,
            balance=0.0,
            kyc_level=0,
            pin_hash=hash_password(DEFAULT_PIN),
            is_active=True,
            agent_float=0.0,
        )
        db.add(user)
        db.commit()

    send_otp(db, phone)
    return {"sent": True}

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)
    otp = payload.otp.strip()

    record = (
        db.query(OTP)
        .filter(OTP.phone == phone, OTP.code == otp, OTP.consumed == False)
        .order_by(OTP.id.desc())
        .first()
    )

    if not record or record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP inválido ou expirado")

    record.consumed = True
    db.commit()

    token = create_access_token(subject=phone)
    return TokenResponse(token=token)
