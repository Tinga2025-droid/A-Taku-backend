from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..audit import audit_log
from ..utils import normalize_phone

router = APIRouter(prefix="/wallet", tags=["Wallet - Cashout"])

@router.post("/cashout")
def wallet_cashout(phone: str, amount: float, pin: str, db: Session = Depends(get_db)):

    phone = normalize_phone(phone)
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return {"success": False, "message": "Conta não encontrada."}

    if user.pin != pin:
        audit_log(db, user.id, "pin_fail_cashout")
        return {"success": False, "message": "PIN incorreto."}

    if user.balance < amount:
        audit_log(db, user.id, "cashout_fail_saldo")
        return {"success": False, "message": "Saldo insuficiente."}

    user.balance -= amount
    db.commit()

    audit_log(db, user.id, "cashout_success", amount=amount)

    return {"success": True, "message": "Cashout solicitado."}
