from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..audit import audit_log
from ..utils import normalize_phone

router = APIRouter(prefix="/wallet", tags=["Wallet - Payments"])

@router.post("/pay")
def wallet_pay(phone: str, service: str, amount: float, pin: str, db: Session = Depends(get_db)):

    phone = normalize_phone(phone)
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return {"success": False, "message": "Conta não encontrada."}

    if user.pin != pin:
        audit_log(db, user.id, "pin_fail_pay_service")
        return {"success": False, "message": "PIN incorreto."}

    if user.balance < amount:
        audit_log(db, user.id, "pay_fail_saldo")
        return {"success": False, "message": "Saldo insuficiente."}

    user.balance -= amount
    db.commit()

    audit_log(db, user.id, f"service_payment_{service}", amount=amount)

    return {"success": True, "message": f"Pagamento '{service}' concluído."}
