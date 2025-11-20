from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ..database import get_db
from ..models import User, Tx, TxType
from ..models_advanced import Ledger
from ..schemas import BalanceResponse, SendRequest, HistoryResponse, TxItem, TransferRequest
from ..deps import get_current_user
from ..wallet_advanced import make_transfer

router = APIRouter(prefix="/wallet", tags=["wallet"])

LIMITS = {0: 10000.0, 1: 50000.0, 2: 500000.0}


@router.get("/balance", response_model=BalanceResponse)
async def balance(
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.refresh(me)
    return BalanceResponse(balance=me.balance)


@router.post("/send")
async def send(
    payload: SendRequest,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_idempotency_key: str | None = Header(default=None),
):
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

    tx = Tx(
        ref=idem,
        type=TxType.TRANSFER,
        from_user_id=me.id,
        to_user_id=to_user.id,
        amount=amount,
        created_at=datetime.utcnow(),
        status="OK",
    )
    db.add(tx)
    db.commit()

    return {"ok": True, "ref": idem}


@router.post("/transfer")
async def transfer(
    payload: TransferRequest,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """Transferência interna usando PIN do usuário autenticado."""
    ok, msg = make_transfer(
        db=db,
        sender_phone=me.phone,
        receiver_phone=payload.receiver,
        amount=payload.amount,
        pin=payload.pin,
    )

    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    return {"success": True, "message": msg}


@router.get("/history", response_model=HistoryResponse)
async def history(
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Tx)
        .filter(or_(Tx.from_user_id == me.id, Tx.to_user_id == me.id))
        .order_by(Tx.id.desc())
        .limit(50)
    )
    items: list[TxItem] = []
    for t in q.all():
        direction = "OUT" if t.from_user_id == me.id else "IN"
        items.append(
            TxItem(
                ref=t.ref,
                amount=t.amount,
                created_at=t.created_at,
                direction=direction,
            )
        )
    return HistoryResponse(items=items)


@router.get("/statement")
async def wallet_statement(
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type: str | None = None,  # "credit" / "debit"
    start: datetime | None = None,
    end: datetime | None = None,
):
    """Extrato baseado no Ledger, paginado e com filtros."""
    filters = [Ledger.user_id == me.id]

    if type:
        filters.append(Ledger.type == type)
    if start:
        filters.append(Ledger.created_at >= start)
    if end:
        filters.append(Ledger.created_at <= end)

    query = db.query(Ledger).filter(and_(*filters)).order_by(Ledger.id.desc())
    rows = query.offset(offset).limit(limit).all()

    return {
        "success": True,
        "count": len(rows),
        "items": [
            {
                "type": row.type,
                "amount": row.amount,
                "balance_after": row.balance_after,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }