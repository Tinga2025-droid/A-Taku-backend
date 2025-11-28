from datetime import datetime, timedelta
import random
import phonenumbers
from sqlalchemy.orm import Session

from .models import User, Role


# ---------------------------------------------------------
# NORMALIZAÇÃO DE NÚMEROS
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# GERADOR DE CÓDIGO DE AGENTE (USANDO USER)
# ---------------------------------------------------------
def generate_agent_code(db: Session):
    last = (
        db.query(User)
        .filter(User.role == Role.AGENT)
        .order_by(User.id.desc())
        .first()
    )
    next_id = (last.id + 1) if last else 1
    return f"AG{next_id:04d}"


# ---------------------------------------------------------
# GERADOR DE TXID
# ---------------------------------------------------------
def generate_txid():
    now = datetime.utcnow()
    rand = random.randint(100000, 999999)
    return f"TX-{now.strftime('%Y%m%d')}-{rand}"


# ---------------------------------------------------------
# SEGURANÇA DE PIN
# ---------------------------------------------------------
def is_locked(user):
    if user.pin_lock_until and user.pin_lock_until > datetime.utcnow():
        return True
    return False


def register_failed_pin(user):
    from app.database import SessionLocal
    db = SessionLocal()

    user.pin_fail_count += 1

    # 3 tentativas -> bloqueio por 5 minutos
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


# ---------------------------------------------------------
# POLÍTICA DE PIN FORTE
# ---------------------------------------------------------
def is_weak_pin(pin: str) -> bool:
    """
    Retorna True se o PIN for fraco (0000, 1234, repetidos, sequências óbvias, etc).
    """
    if not pin or len(pin) != 4 or not pin.isdigit():
        return True

    fracos = {
        "0000", "1111", "2222", "3333", "4444",
        "5555", "6666", "7777", "8888", "9999",
        "1234", "4321", "0123", "3210"
    }
    if pin in fracos:
        return True

    # sequências crescentes
    seq = "0123456789"
    if pin in seq:
        return True

    # sequências decrescentes
    if pin in seq[::-1]:
        return True

    return False
