from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import get_db
from ..models import User, Tx, TxType
from ..schemas import BalanceResponse, SendRequest, HistoryResponse, TxItem
from ..deps import get_current_user

router = APIRouter(prefix="/wallet", tags=["wallet"])

LIMITS = {0: 10000.0, 1: 50000.0, 2: 500000.0}

@router.get("/balance", response_model=BalanceResponse)
async def balance(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.refresh(me)
    return BalanceResponse(balance=me.balance)

@router.post("/send")
async def send(payload: SendRequest, me: User = Depends(get_current_user), db: Session = Depends(get_db), 
               x_idempotency_key: str | None = Header(default=None)):
    to_phone = payload.to.strip()
    amount = float(payload.amount)
    if amount <= 0:
        raise HTTPException(400, detail="Valor inválido")
    limit = LIMITS.get(me.kyc_level, 0)
    if amount > limit:
        raise HTTPException(403, detail=f"Limite por transação excedido para KYC {me.kyc_level}")
    to_user = db.query(User).filter(User.phone == to_phone).first()
    if not to_user:
        raise HTTPException(404, detail="Destinatário não encontrado")
    idem = x_idempotency_key or payload.idempotency_key or f"{me.id}:{to_user.id}:{amount}"
    existing = db.query(Tx).filter(Tx.ref == idem).first()
    if existing:
        return {"ok": True, "ref": existing.ref}
    db.refresh(me)
    if me.balance < amount:
        raise HTTPException(402, detail="Saldo insuficiente")
    me.balance -= amount
    to_user.balance += amount
    tx = Tx(ref=idem, type=TxType.TRANSFER, from_user_id=me.id, to_user_id=to_user.id, amount=amount)
    db.add(tx); db.commit()
    return {"ok": True, "ref": idem}

@router.get("/history", response_model=HistoryResponse)
async def history(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Tx).filter(or_(Tx.from_user_id == me.id, Tx.to_user_id == me.id)).order_by(Tx.id.desc()).limit(50)
    items: list[TxItem] = []
    for t in q.all():
        direction = "OUT" if t.from_user_id == me.id else "IN"
        items.append(TxItem(ref=t.ref, amount=t.amount, created_at=t.created_at, direction=direction))
    return HistoryResponse(items=items)
