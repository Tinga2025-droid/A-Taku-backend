from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..otp_provider import create_or_update_otp, verify_otp
from ..auth import create_access_token
from ..models import User

router = APIRouter(prefix="/auth", tags=["OTP Auth"])

class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp: str
    pin: str

@router.post("/send-otp")
def send_otp(data: OTPRequest, db: Session = Depends(get_db)):
    create_or_update_otp(db, data.phone)
    return {"ok": True, "message": "OTP enviado"}

@router.post("/login-otp")
def login_with_otp(data: OTPVerify, db: Session = Depends(get_db)):
    ok, message = verify_otp(db, data.phone, data.otp)

    if not ok:
        return {"ok": False, "detail": message}

    user = db.query(User).filter(User.phone == data.phone).first()
    if not user:
        return {"ok": False, "detail": "Usuário não encontrado."}

    if not user.verify_pin(data.pin):
        return {"ok": False, "detail": "PIN incorreto."}

    token = create_access_token(user.phone)
    return {"ok": True, "token": token, "user": user.phone}
