from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models_advanced import Ledger
from ..utils import normalize_phone
from ..models import User

router = APIRouter(prefix="/wallet", tags=["Wallet - Statement"])

@router.get("/statement")
def wallet_statement(phone: str, db: Session = Depends(get_db)):
    phone = normalize_phone(phone)
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return {"success": False, "message": "Conta não encontrada."}

    data = db.query(Ledger).filter(Ledger.user_id == user.id).order_by(Ledger.id.desc()).limit(20).all()

    return {"success": True, "history": [
        {
            "type": row.type,
            "amount": row.amount,
            "balance_after": row.balance_after,
            "created_at": row.created_at
        }
        for row in data
    ]}
