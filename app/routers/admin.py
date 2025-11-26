# app/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FeesConfig, User
from ..schemas import FeesPayload
from ..auth import verify_password
from ..utils import normalize_phone

router = APIRouter(prefix="/admin", tags=["admin"])


# -----------------------------
# 🔐 VERIFICAR SE É ADMIN
# -----------------------------
def ensure_admin(db: Session, phone: str, pin: str):
    phone = normalize_phone(phone)
    admin = db.query(User).filter(User.phone == phone, User.role == "ADMIN").first()

    if not admin or not verify_password(pin, admin.pin_hash):
        raise HTTPException(status_code=403, detail="Acesso negado: não é ADMIN")

    return admin


# -----------------------------
# ⚙️ 1. DEFINIR TAXAS
# -----------------------------
@router.post("/fees")
def set_fees(
    payload: FeesPayload,
    db: Session = Depends(get_db),
):
    """
    Configura parâmetros de taxa.
    - fee_owner_pct → % da taxa que vai para o dono
    - o restante vai para o agente
    """
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
    phone: str,
    full_name: str,
    pin: str,
    agent_code: str,
    admin_phone: str,
    admin_pin: str,
    db: Session = Depends(get_db),
):
    """
    ADMIN cria um agente.
    """
    ensure_admin(db, admin_phone, admin_pin)

    phone = normalize_phone(phone)

    user = db.query(User).filter(User.phone == phone).first()
    if user:
        raise HTTPException(status_code=400, detail="Usuário já existe")

    new_agent = User(
        phone=phone,
        full_name=full_name,
        role="AGENT",
        agent_code=agent_code,
        is_active=True,
        balance=0.0,
        agent_float=0.0,
        pin_hash=verify_password(pin, pin),  # será corrigido no schemas
    )

    db.add(new_agent)
    db.commit()
    return {"ok": True, "agent": phone}


# -----------------------------
# 💰 3. DEFINIR FLOAT DO AGENTE
# -----------------------------
@router.post("/agent/set-float")
def set_agent_float(
    phone: str,
    amount: float,
    admin_phone: str,
    admin_pin: str,
    db: Session = Depends(get_db),
):
    """
    ADMIN define o float do agente.
    """
    ensure_admin(db, admin_phone, admin_pin)

    phone = normalize_phone(phone)
    agent = db.query(User).filter(User.phone == phone, User.role == "AGENT").first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    agent.agent_float = amount
    db.commit()

    return {"ok": True, "new_float": amount}


# -----------------------------
# 🔐 4. VERIFICAR STATUS GERAL
# -----------------------------
@router.get("/status")
def admin_status(db: Session = Depends(get_db)):
    """
    Retorna estado básico do sistema:
    - número de usuários
    - agentes
    - taxa configurada
    """
    users = db.query(User).count()
    agents = db.query(User).filter(User.role == "AGENT").count()
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

    db.commit()
    return {"ok": True}