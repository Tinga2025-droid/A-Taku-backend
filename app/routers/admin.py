# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FeesConfig, User, Role
from ..schemas import FeesPayload
from ..auth import verify_password, hash_password     # 🔥 AQUI AJUSTADO
from ..utils import normalize_phone

router = APIRouter(prefix="/admin", tags=["admin"])


# -----------------------------
# 🔐 VERIFICAR SE É ADMIN
# -----------------------------
def ensure_admin(db: Session, phone: str, pin: str):
    phone = normalize_phone(phone)
    admin = db.query(User).filter(
        User.phone == phone,
        User.role == Role.ADMIN
    ).first()

    if not admin or not verify_password(pin, admin.pin_hash):
        raise HTTPException(status_code=403, detail="Acesso negado: não é ADMIN")

    return admin


# -----------------------------
# ⚙️ 1. DEFINIR TAXAS
# -----------------------------
@router.post("/fees")
def set_fees(payload: FeesPayload, db: Session = Depends(get_db)):
    cfg = db.query(FeesConfig).get(1)
    if not cfg:
        cfg = FeesConfig(id=1)
        db.add(cfg)

    cfg.cashout_fee_pct = payload.cashout_fee_pct
    cfg.cashout_fee_min = payload.cashout_fee_min
    cfg.cashout_fee_max = payload.cashout_fee_max
    cfg.fee_owner_pct = payload.fee_owner_pct

    db.commit()
    return {"ok": True}


# -----------------------------
# 🧩 2. CRIAR AGENTE
# -----------------------------
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


# -----------------------------
# 💰 3. DEFINIR FLOAT DO AGENTE
# -----------------------------
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


# -----------------------------
# 🔐 4. STATUS GERAL
# -----------------------------
@router.get("/status")
def admin_status(db: Session = Depends(get_db)):
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


# -----------------------------
# 🛠️ DEBUG — LISTAR TODOS OS USERS
# -----------------------------
@router.get("/debug/users")
def debug_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "phone": u.phone,
            "role": u.role.value,
            "full_name": u.full_name,
            "agent_code": u.agent_code,
            "agent_float": u.agent_float,
            "pin_hash": u.pin_hash,
            "is_active": u.is_active,
        }
        for u in users
    ]
