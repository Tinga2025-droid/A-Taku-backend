from datetime import datetime, timedelta
import random
import phonenumbers
from sqlalchemy.orm import Session
from .models import Agent


def normalize_phone(raw: str, default_region: str = "MZ") -> str:
    raw = (raw or "").strip()

    try:
        num = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise ValueError("Telefone inválido")

    if digits.startswith("258"):
        candidate = "+" + digits
    elif len(digits) == 9 and digits.startswith(("82", "83", "84", "85", "86", "87")):
        candidate = "+258" + digits
    else:
        candidate = "+" + digits

    try:
        num = phonenumbers.parse(candidate, default_region)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    raise ValueError("Telefone inválido ou não suportado")


def generate_agent_code(db: Session):
    last = db.query(Agent).order_by(Agent.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    return f"AG{next_id:04d}"


def generate_txid():
    now = datetime.utcnow()
    rand = random.randint(100000, 999999)
    return f"TX-{now.strftime('%Y%m%d')}-{rand}"


def is_locked(user):
    if user.pin_lock_until and user.pin_lock_until > datetime.utcnow():
        return True
    return False


def register_failed_pin(user):
    from app.database import SessionLocal
    db = SessionLocal()

    user.pin_fail_count += 1

    if user.pin_fail_count >= 3:
        user.pin_lock_until = datetime.utcnow() + timedelta(minutes=5)
        user.pin_fail_count = 0
        db.commit()
        db.close()
        return "LOCKED"

    db.commit()
    db.close()
    return "FAIL"


def reset_pin_fail(user):
    from app.database import SessionLocal
    db = SessionLocal()
    user.pin_fail_count = 0
    user.pin_lock_until = None
    db.commit()
    db.close()