# app/otp_provider.py
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .otp_models import OTPCode

# ------------------------------
# Gera um OTP de 6 dígitos
# ------------------------------
def generate_otp():
    return f"{random.randint(100000, 999999)}"

# ------------------------------
# Envia SMS (placeholder)
# ------------------------------
def send_otp_sms(phone: str, otp: str):
    print(f"[SMS ENVIADO] OTP para {phone}: {otp}")

# ------------------------------
# Cria ou atualiza OTP no banco
# ------------------------------
def create_or_update_otp(db: Session, phone: str):
    otp = generate_otp()

    record = db.query(OTPCode).filter(OTPCode.phone == phone).first()

    if record:
        record.otp = otp
        record.created_at = datetime.utcnow()
        record.attempts = 0
        record.blocked_until = None
    else:
        record = OTPCode(
            phone=phone,
            otp=otp,
            created_at=datetime.utcnow(),
            attempts=0,
            blocked_until=None
        )
        db.add(record)

    db.commit()
    send_otp_sms(phone, otp)
    return otp

# ------------------------------
# Verifica o OTP
# ------------------------------
def verify_otp(db: Session, phone: str, otp_input: str):
    record = db.query(OTPCode).filter(OTPCode.phone == phone).first()

    if not record:
        return False, "OTP não encontrado."

    if record.is_blocked():
        return False, "Número temporariamente bloqueado. Tente mais tarde."

    if record.is_expired():
        return False, "OTP expirado. Peça um novo."

    if record.otp == otp_input:
        db.delete(record)
        db.commit()
        return True, "OTP válido."

    # Tentativa inválida
    record.attempts += 1

    if record.attempts >= 3:
        record.blocked_until = datetime.utcnow() + timedelta(minutes=10)

    db.commit()
    return False, "OTP inválido."

# ------------------------------
# Função simples para o auth.py
# ------------------------------
def send_otp(phone: str, db: Session):
    """
    Wrapper para facilitar import no auth.py
    """
    otp = create_or_update_otp(db, phone)
    return otp