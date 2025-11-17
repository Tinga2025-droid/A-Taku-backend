from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..wallet_advanced import make_transfer
from ..utils import normalize_phone

router = APIRouter(prefix="/wallet", tags=["Wallet - Transfer"])

@router.post("/transfer")
def wallet_transfer(sender_phone: str, receiver_phone: str, amount: float, pin: str, db: Session = Depends(get_db)):

    sender_phone = normalize_phone(sender_phone)
    receiver_phone = normalize_phone(receiver_phone)

    ok, msg = make_transfer(db, sender_phone, receiver_phone, amount, pin)

    return {"success": ok, "message": msg}
