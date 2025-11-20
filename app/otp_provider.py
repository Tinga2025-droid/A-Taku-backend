import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .otp_models import OTPCode  # modelo que já tens no projeto


def generate_otp() -> str:
    """Gera um OTP de 6 dígitos."""
    return f"{random.randint(100000, 999999)}"


def send_otp_sms(phone: str, otp: str) -> None:
    """Placeholder de envio de SMS. Trocar pela integração real (AfricasTalking, etc.)."""
    print(f"[SMS ENVIADO] OTP para {phone}: {otp}")


def create_or_update_otp(db: Session, phone: str) -> str:
    """Cria ou atualiza um OTP para o número indicado."""
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
            blocked_until=None,
        )
        db.add(record)

    db.commit()
    send_otp_sms(phone, otp)
    return otp


def verify_otp(db: Session, phone: str, otp_input: str):
    """Verifica OTP com expiração e bloqueio por tentativas falhadas."""
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


def send_otp(phone: str, db: Session):
    """Wrapper simples se quiser chamar só send_otp em outros módulos."""
    otp = create_or_update_otp(db, phone)
    return otp