from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from ..database import get_db, Base, engine
from ..models import User, OTP
from ..schemas import OTPRequest, LoginRequest, TokenResponse
from ..otp_provider import send_otp
from ..auth import create_access_token

Base.metadata.create_all(bind=engine)
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/otp")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, balance=0.0, kyc_level=0)
        db.add(user)
        db.commit()
    send_otp(db, phone)
    return {"sent": True}

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    phone, otp = payload.phone.strip(), payload.otp.strip()
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
