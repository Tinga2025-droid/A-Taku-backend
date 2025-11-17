from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models import User
from ..database import get_db
from ..audit import audit_log
from ..utils import normalize_phone

router = APIRouter(prefix="/agent", tags=["Agent Operations"])

@router.post("/deposit")
def agent_deposit(agent_phone: str, customer_phone: str, amount: float, db: Session = Depends(get_db)):

    agent_phone = normalize_phone(agent_phone)
    customer_phone = normalize_phone(customer_phone)

    agent = db.query(User).filter(User.phone == agent_phone, User.role == "agent").first()
    customer = db.query(User).filter(User.phone == customer_phone).first()

    if not agent:
        return {"success": False, "message": "Agente não encontrado."}

    if not customer:
        return {"success": False, "message": "Cliente não encontrado."}

    customer.balance += amount
    db.commit()

    audit_log(db, agent.id, "agent_deposit", amount=amount, metadata=f"para {customer_phone}")

    return {"success": True, "message": "Depósito realizado pelo agente."}
