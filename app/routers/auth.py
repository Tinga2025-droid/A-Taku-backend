from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import OTPRequest, LoginRequest, TokenResponse
from ..otp_provider import create_or_update_otp, verify_otp
from ..auth import create_access_token, hash_password, verify_password
from ..utils import normalize_phone, is_locked, register_failed_pin, reset_pin_fail, is_weak_pin

router = APIRouter(prefix="/auth", tags=["auth"])

DEFAULT_PIN = "0000"


@router.post("/otp")
def request_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)

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

    if is_locked(user):
        raise HTTPException(status_code=400, detail="Conta temporariamente bloqueada. Tente mais tarde.")

    # Se ainda não tiver PIN definido -> definir agora, mas com política forte
    if not user.pin_hash:
        if is_weak_pin(payload.pin):
            raise HTTPException(status_code=400, detail="PIN fraco. Evite 0000, 1234, 1111, etc.")
        user.pin_hash = hash_password(payload.pin)
        reset_pin_fail(user)
        db.commit()
    else:
        # Já tem PIN -> validar login
        if not verify_password(payload.pin, user.pin_hash):
            status = register_failed_pin(user)
            db.commit()

            if status == "LOCKED":
                raise HTTPException(status_code=400, detail="PIN incorreto 3 vezes. Conta bloqueada por 5 minutos.")

            raise HTTPException(status_code=400, detail="PIN incorreto.")

        reset_pin_fail(user)
        db.commit()

    token = create_access_token(subject=phone)
    return TokenResponse(token=token)