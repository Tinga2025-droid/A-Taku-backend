from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import OTPRequest, LoginRequest, TokenResponse
from ..otp_provider import create_or_update_otp, verify_otp
from ..auth import create_access_token, hash_password, verify_password
from ..utils import normalize_phone

router = APIRouter(prefix="/auth", tags=["auth"])

DEFAULT_PIN = "0000"


@router.post("/otp")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)

    # Garante que a conta existe (estilo USSD: auto-criação)
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(
            phone=phone,
            balance=0.0,
            kyc_level=0,
            is_active=True,
            pin_hash=hash_password(DEFAULT_PIN),
            agent_float=0.0,
        )
        db.add(user)
        db.commit()

    create_or_update_otp(db, phone)
    return {"ok": True, "message": "OTP enviado"}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)

    ok, message = verify_otp(db, phone, payload.otp)
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado.")

    # Primeiro login (ou legacy sem PIN): define PIN
    if not user.pin_hash:
        user.pin_hash = hash_password(payload.pin)
        db.add(user)
        db.commit()
    else:
        if not verify_password(payload.pin, user.pin_hash):
            raise HTTPException(status_code=400, detail="PIN incorreto.")

    token = create_access_token(subject=phone)
    return TokenResponse(token=token)