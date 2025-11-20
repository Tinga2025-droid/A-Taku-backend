import json

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..database import get_db
from ..models import User, Role, Tx, TxType, FeesConfig
from ..schemas import AgentLoginRequest, DepositRequest, CashoutRequest
from ..auth import create_access_token, verify_password, hash_password, decode_token
from ..utils import normalize_phone

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/login")
def login_agent(payload: AgentLoginRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)
    agent = db.query(User).filter(User.phone == phone, User.role == Role.AGENT).first()
    if not agent or not agent.pin_hash or not verify_password(payload.pin, agent.pin_hash):
        raise HTTPException(401, detail="Credenciais inválidas")
    return {"token": create_access_token(subject=phone)}


@router.post("/seed")
def seed_agent(
    phone: str,
    pin: str,
    float_amount: float = 0.0,
    db: Session = Depends(get_db),
):
    """Cria ou atualiza um agente com e-float inicial (uso admin/seed)."""
    phone = normalize_phone(phone)
    ag = db.query(User).filter(User.phone == phone).first()
    if not ag:
        ag = User(phone=phone, role=Role.AGENT, agent_float=0.0, balance=0.0)
        db.add(ag)
    ag.role = Role.AGENT
    ag.pin_hash = hash_password(pin)
    ag.agent_float = float_amount
    db.commit()
    return {"ok": True}


@router.post("/deposit")
async def deposit(
    payload: DepositRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, detail="Missing token")

    agent_phone = decode_token(authorization.split(" ", 1)[1])
    agent = db.query(User).filter(User.phone == agent_phone, User.role == Role.AGENT).first()
    if not agent:
        raise HTTPException(401, detail="Agente inválido")

    customer_phone = normalize_phone(payload.customer_phone)
    customer = db.query(User).filter(User.phone == customer_phone).first()
    if not customer:
        # cria conta base para o cliente
        customer = User(phone=customer_phone, balance=0.0)
        db.add(customer)
        db.commit()
        db.refresh(customer)

    amount = float(payload.amount)
    if amount <= 0:
        raise HTTPException(400, detail="Valor inválido")

    if agent.agent_float < amount:
        raise HTTPException(402, detail="Agente sem e-float suficiente")

    ref = payload.idempotency_key or f"DEP-{agent.id}-{customer.id}-{amount}"
    if db.query(Tx).filter(Tx.ref == ref).first():
        return {"ok": True, "ref": ref}

    try:
        agent.agent_float -= amount
        customer.balance += amount

        tx = Tx(
            ref=ref,
            type=TxType.DEPOSIT,
            from_user_id=agent.id,
            to_user_id=customer.id,
            amount=amount,
            meta=json.dumps({"channel": "agent"}),
            status="OK",
        )
        db.add(tx)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Erro interno ao processar depósito")

    return {"ok": True, "ref": ref, "customer_balance": customer.balance}


@router.post("/cashout")
async def cashout(
    payload: CashoutRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, detail="Missing token")

    agent_phone = decode_token(authorization.split(" ", 1)[1])
    agent = db.query(User).filter(User.phone == agent_phone, User.role == Role.AGENT).first()
    if not agent:
        raise HTTPException(401, detail="Agente inválido")

    customer_phone = normalize_phone(payload.customer_phone)
    customer = db.query(User).filter(User.phone == customer_phone).first()
    if not customer:
        raise HTTPException(404, detail="Cliente não encontrado")

    amount = float(payload.amount)
    if amount <= 0:
        raise HTTPException(400, detail="Valor inválido")

    cfg = db.query(FeesConfig).get(1)
    if not cfg:
        cfg = FeesConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    fee_raw = amount * (cfg.cashout_fee_pct / 100.0)
    fee_capped = max(cfg.cashout_fee_min, min(fee_raw, cfg.cashout_fee_max))
    total_debit = amount + fee_capped

    if customer.balance < total_debit:
        raise HTTPException(402, detail="Saldo do cliente insuficiente (valor + taxa)")

    ref = payload.idempotency_key or f"CSO-{agent.id}-{customer.id}-{amount}"
    if db.query(Tx).filter(Tx.ref == ref).first():
        return {"ok": True, "ref": ref}

    try:
        customer.balance -= total_debit
        agent.agent_float += amount

        owner_part = fee_capped * (cfg.fee_owner_pct / 100.0)
        agent_part = fee_capped - owner_part

        tx_main = Tx(
            ref=ref,
            type=TxType.CASHOUT,
            from_user_id=customer.id,
            to_user_id=agent.id,
            amount=amount,
            meta=json.dumps({"channel": "agent_cashout"}),
            status="OK",
        )

        tx_fee_owner = Tx(
            ref=f"{ref}-FOWN",
            type=TxType.COMMISSION,
            from_user_id=customer.id,
            to_user_id=None,
            amount=owner_part,
            meta=json.dumps({"role": "owner"}),
            status="OK",
        )

        tx_fee_agent = Tx(
            ref=f"{ref}-FAGT",
            type=TxType.COMMISSION,
            from_user_id=customer.id,
            to_user_id=agent.id,
            amount=agent_part,
            meta=json.dumps({"role": "agent"}),
            status="OK",
        )

        db.add_all([tx_main, tx_fee_owner, tx_fee_agent])
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, detail="Erro interno ao processar cashout")

    return {
        "ok": True,
        "ref": ref,
        "fee": fee_capped,
        "split": {"owner": owner_part, "agent": agent_part},
        "customer_balance": customer.balance,
    }
