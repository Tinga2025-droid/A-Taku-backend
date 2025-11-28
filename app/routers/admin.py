import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FeesConfig, User, Role
from ..schemas import FeesPayload
from ..auth import verify_password, hash_password
from ..utils import normalize_phone, is_weak_pin

router = APIRouter(prefix="/admin", tags=["admin"])

DEBUG_ADMIN = os.getenv("DEBUG_ADMIN", "false").lower() == "true"


def ensure_debug_enabled():
    if not DEBUG_ADMIN:
        # Em produção, isto impede uso dos endpoints /debug/*
        raise HTTPException(status_code=403, detail="Debug desativado em produção")


# -------------------------------------------------------------------
# 🔐 FUNÇÃO -> Validar ADMIN
# -------------------------------------------------------------------
def ensure_admin(db: Session, phone: str, pin: str):
    phone = normalize_phone(phone)
    admin = db.query(User).filter(
        User.phone == phone,
        User.role == Role.ADMIN
    ).first()

    if not admin or not verify_password(pin, admin.pin_hash):
        raise HTTPException(status_code=403, detail="Acesso negado: não é ADMIN")

    return admin


# -------------------------------------------------------------------
# ⚙️ DEFINIR TAXAS DO SISTEMA
# -------------------------------------------------------------------
@router.post("/fees")
def set_fees(
    payload: FeesPayload,
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db)
):
    ensure_admin(db, admin_phone, admin_pin)

    cfg = db.query(FeesConfig).get(1)
    if not cfg:
        cfg = FeesConfig(id=1)
        db.add(cfg)

    cfg.cashout_fee_pct = payload.cashout_fee_pct
    cfg.cashout_fee_min = payload.cashout_fee_min
    cfg.cashout_fee_max = payload.cashout_fee_max
    cfg.fee_owner_pct = payload.fee_owner_pct

    db.commit()
    return {"ok": True, "msg": "Taxas atualizadas"}


# -------------------------------------------------------------------
# 🧩 CRIAR AGENTE
# -------------------------------------------------------------------
@router.post("/agent/create")
def create_agent(
    phone: str = Query(...),
    full_name: str = Query(...),
    pin: str = Query(...),
    agent_code: str = Query(...),
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)

    if is_weak_pin(pin):
        raise HTTPException(status_code=400, detail="PIN fraco para agente. Evite 0000, 1234, etc.")

    phone = normalize_phone(phone)

    if db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")

    new_agent = User(
        phone=phone,
        full_name=full_name,
        role=Role.AGENT,
        agent_code=agent_code,
        is_active=True,
        balance=0.0,
        agent_float=0.0,
        pin_hash=hash_password(pin),
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {"ok": True, "created_agent": new_agent.phone}


# -------------------------------------------------------------------
# 💰 DEFINIR FLOAT DO AGENTE
# -------------------------------------------------------------------
@router.post("/agent/set-float")
def set_agent_float(
    phone: str = Query(...),
    amount: float = Query(...),
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)

    phone = normalize_phone(phone)

    agent = db.query(User).filter(
        User.phone == phone,
        User.role == Role.AGENT
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    agent.agent_float = amount
    db.commit()
    return {"ok": True, "new_float": amount}


# -------------------------------------------------------------------
# 🔐 STATUS GERAL DO SISTEMA
# -------------------------------------------------------------------
@router.get("/status")
def admin_status(
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)

    users = db.query(User).count()
    agents = db.query(User).filter(User.role == Role.AGENT).count()
    fees = db.query(FeesConfig).first()

    return {
        "users": users,
        "agents": agents,
        "fees": {
            "cashout_pct": fees.cashout_fee_pct if fees else None,
            "cashout_min": fees.cashout_fee_min if fees else None,
            "cashout_max": fees.cashout_fee_max if fees else None,
            "owner_pct": fees.fee_owner_pct if fees else None,
        },
    }


# -------------------------------------------------------------------
# 🧨 DEBUG — Reset total do DB (AGORA REALMENTE SEGURO)
# -------------------------------------------------------------------
@router.post("/debug/reset-db")
def reset_db(
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)
    ensure_debug_enabled()

    from ..database import engine, Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    return {"ok": True, "msg": "Base reiniciada com sucesso"}


# -------------------------------------------------------------------
# 🔍 DEBUG — Ver dados de um usuário (SAFE)
# -------------------------------------------------------------------
@router.get("/debug/user")
def debug_user(
    phone: str = Query(...),
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)
    ensure_debug_enabled()

    try:
        phone = normalize_phone(phone)
    except Exception:
        raise HTTPException(status_code=400, detail="Telefone inválido")

    u = db.query(User).filter(User.phone == phone).first()
    if not u:
        return {"exists": False}

    return {
        "exists": True,
        "id": u.id,
        "phone": u.phone,
        "full_name": u.full_name,
        "role": u.role.value if hasattr(u.role, "value") else str(u.role),
        "balance": u.balance,
        "agent_code": u.agent_code,
        "agent_float": u.agent_float,
        "is_active": u.is_active,
        "pin_hash": "(hidden)",
        "created_at": str(u.created_at),
    }


# -------------------------------------------------------------------
# 🛠️ DEBUG — Listar todos usuários (AGORA SEGURO)
# -------------------------------------------------------------------
@router.get("/debug/users")
def debug_users(
    admin_phone: str = Query(...),
    admin_pin: str = Query(...),
    db: Session = Depends(get_db),
):
    ensure_admin(db, admin_phone, admin_pin)
    ensure_debug_enabled()

    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "phone": u.phone,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "full_name": u.full_name,
            "agent_code": u.agent_code,
            "agent_float": u.agent_float,
            "is_active": u.is_active,
            "pin_hash": "(hidden)",
        }
        for u in users
    ]