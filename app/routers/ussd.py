# app/routers/ussd.py
from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime
from passlib.context import CryptContext

from ..database import get_db
from ..models import User, Tx, TxType, FeesConfig

router = APIRouter(tags=["ussd"])

# --- Configs de negócio ---
INITIAL_BONUS = 25.0
DEFAULT_PIN = "0000"
AIRTIME_MIN = 20

# PBKDF2
pwd = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

# -------- Helpers --------
def e164(phone: str) -> str:
    p = phone.strip().replace(" ", "")
    if p.startswith("00"):
        p = "+" + p[2:]
    if not p.startswith("+"):
        if p.startswith(("84", "85", "86", "82")):
            p = "+258" + p
        elif p.startswith("258"):
            p = "+" + p
        else:
            p = "+" + p
    return p

def get_or_create_user(db: Session, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user
    user = User(
        phone=phone,
        kyc_level=0,
        is_active=True,
        balance=INITIAL_BONUS,
        agent_float=0.0,
        pin_hash=pwd.hash(DEFAULT_PIN),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    tx = Tx(
        ref=f"BONUS-{int(datetime.utcnow().timestamp())}-{user.id}",
        type=TxType.DEPOSIT,
        to_user_id=user.id,
        amount=INITIAL_BONUS,
        meta="Bônus de boas-vindas",
        status="OK",
    )
    db.add(tx)
    db.commit()
    return user

def verify_pin(user: User, pin: str) -> bool:
    try:
        return pwd.verify(pin, user.pin_hash) if user.pin_hash else False
    except Exception:
        return False

def set_pin(user: User, new_pin: str, db: Session):
    user.pin_hash = pwd.hash(new_pin)
    db.add(user)
    db.commit()

def safe_int(s: str) -> int | None:
    try:
        return int(s)
    except Exception:
        return None

def end(text: str) -> str:
    return f"END {text}"

def con(text: str) -> str:
    return f"CON {text}"

def balance_line(user: User) -> str:
    return f"Saldo: {user.balance:.2f} MZN"

def last_n_txs(db: Session, user: User, n: int = 5):
    return (
        db.query(Tx)
        .filter((Tx.from_user_id == user.id) | (Tx.to_user_id == user.id))
        .order_by(Tx.created_at.desc())
        .limit(n)
        .all()
    )

def apply_cashout_fees(db: Session, amount: float):
    cfg = db.query(FeesConfig).first()
    if not cfg:
        pct, fmin, fmax = 1.5, 5.0, 150.0
    else:
        pct, fmin, fmax = cfg.cashout_fee_pct, cfg.cashout_fee_min, cfg.cashout_fee_max
    fee = amount * (pct / 100.0)
    fee = max(fmin, min(fee, fmax))
    return (fee, amount + fee)

# -------- Menus --------
def main_menu() -> str:
    return con(
        "Bem-vindo ao A-Taku\n"
        "1. Criar conta\n"
        "2. Entrar\n"
        "3. Ver saldo / Minha conta\n"
        "4. Transferir dinheiro\n"
        "5. Levantar (cashout)\n"
        "6. Pagar serviços\n"
        "7. Extrato\n"
        "8. Comprar crédito"
    )

def require_pin_menu(prefix: str = "") -> str:
    return con(prefix + "Digite seu PIN (4 dígitos):")

def force_change_pin_menu(prefix: str = "") -> str:
    return con(prefix + "Defina novo PIN (4 dígitos):")

# -------------------------------------------------
#  USSD CALLBACK (CORRIGIDO PARA Text/Plain)
# -------------------------------------------------
@router.post("/ussd", response_class=PlainTextResponse)
def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    db: Session = Depends(get_db),
):
    phone = e164(phoneNumber)
    parts = [p for p in text.split("*") if p != ""] if text else []

    # entrada
    if not parts:
        return main_menu()

    # --- 1) Criar conta ---
    if parts[0] == "1":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            if len(parts) == 1:
                return force_change_pin_menu("Conta criada. Bónus 25 MZN.\n")
            elif len(parts) == 2:
                new_pin = parts[1]
                if len(new_pin) != 4 or (not new_pin.isdigit()) or new_pin == DEFAULT_PIN:
                    return force_change_pin_menu("PIN inválido. Use 4 dígitos (≠ 0000).\n")
                set_pin(user, new_pin, db)
                return end("PIN definido com sucesso. Faça operações no menu principal.")
        return end("Sua conta já existe. Utilize as opções do menu.")

    # --- 2) Entrar ---
    if parts[0] == "2":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            if len(parts) == 1:
                return force_change_pin_menu("PIN padrão detectado.\n")
            elif len(parts) == 2:
                new_pin = parts[1]
                if len(new_pin) != 4 or (not new_pin.isdigit()) or new_pin == DEFAULT_PIN:
                    return force_change_pin_menu("PIN inválido. Use 4 dígitos (≠ 0000).\n")
                set_pin(user, new_pin, db)
                return end("PIN atualizado. Pode continuar a usar o serviço.")
        if len(parts) == 1:
            return require_pin_menu("Entrar — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido ou expirado.")
            return end(f"Login OK. {balance_line(user)}")

    # --- 3) Saldo ---
    if parts[0] == "3":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Ver Saldo — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            return end(balance_line(user))

    # --- 4) Transferência ---
    if parts[0] == "4":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Transferir — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            return con("Digite número do destinatário:")
        elif len(parts) == 3:
            to_raw = parts[2]
            to_phone = e164(to_raw)
            if to_phone == phone:
                return con("Não pode transferir para si mesmo.\nDigite outro número:")
            return con("Digite o valor (MZN):")
        elif len(parts) == 4:
            amount = safe_int(parts[3])
            if amount is None or amount <= 0:
                return con("Valor inválido. Digite novamente:")
            to_phone = e164(parts[2])
            to_user = get_or_create_user(db, to_phone)
            if user.balance < amount:
                return end("Saldo insuficiente.")
            user.balance -= float(amount)
            to_user.balance += float(amount)
            db.add(user); db.add(to_user)
            tx = Tx(
                ref=f"TX-{int(datetime.utcnow().timestamp())}-{user.id}-{to_user.id}",
                type=TxType.TRANSFER,
                from_user_id=user.id,
                to_user_id=to_user.id,
                amount=float(amount),
                meta=f"USSD transfer {phone} -> {to_phone}",
                status="OK",
            )
            db.add(tx)
            db.commit()
            return end(f"Transferência OK: {amount} MZN para {to_phone}. {balance_line(user)}")

    # --- 5) Cashout ---
    if parts[0] == "5":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Levantar — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            return con("Digite o valor a levantar:")
        elif len(parts) == 3:
            amount = safe_int(parts[2])
            if amount is None or amount <= 0:
                return con("Valor inválido. Digite um inteiro:")
            fee, total = apply_cashout_fees(db, float(amount))
            if user.balance < total:
                return end("Saldo insuficiente para cobrir valor + taxa.")
            user.balance -= total
            db.add(user)
            tx = Tx(
                ref=f"CASH-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.CASHOUT,
                from_user_id=user.id,
                to_user_id=None,
                amount=float(amount),
                meta=f"fee={fee:.2f}",
                status="OK",
            )
            db.add(tx)
            db.commit()
            return end(f"Levantamento OK: {amount:.2f} MZN (taxa {fee:.2f}). {balance_line(user)}")

    # --- 6) Pagamentos ---
    if parts[0] == "6":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Pagar — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            return con("Digite referência do serviço:")
        elif len(parts) == 3:
            return con("Digite o valor (MZN):")
        elif len(parts) == 4:
            ref = parts[2]
            amount = safe_int(parts[3])
            if amount is None or amount <= 0:
                return con("Valor inválido. Digite novamente:")
            if user.balance < amount:
                return end("Saldo insuficiente.")
            user.balance -= float(amount)
            db.add(user)
            tx = Tx(
                ref=f"PAY-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.TRANSFER,
                from_user_id=user.id,
                to_user_id=None,
                amount=float(amount),
                meta=f"service_ref={ref}",
                status="OK",
            )
            db.add(tx)
            db.commit()
            return end(f"Pagamento OK ref {ref}: {amount} MZN. {balance_line(user)}")

    # --- 7) Extrato ---
    if parts[0] == "7":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Extrato — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            txs = last_n_txs(db, user, 5)
            if not txs:
                return end("Sem movimentos.")
            lines = []
            for t in txs:
                direction = "OUT" if t.from_user_id == user.id else "IN"
                when = t.created_at.strftime("%d/%m %H:%M")
                ttype = str(t.type)[:4] if hasattr(t, "type") else "TX"
                lines.append(f"{when} {direction} {ttype} {t.amount:.2f}")
            body = "\n".join(lines)
            return end(f"{body}\n{balance_line(user)}")

    # --- 8) Comprar crédito ---
    if parts[0] == "8":
        user = get_or_create_user(db, phone)
        if verify_pin(user, DEFAULT_PIN):
            return force_change_pin_menu("Defina um novo PIN para continuar.\n")
        if len(parts) == 1:
            return require_pin_menu("Comprar Crédito — ")
        elif len(parts) == 2:
            pin = parts[1]
            if not verify_pin(user, pin):
                return end("PIN inválido.")
            return con(f"Digite o valor (mínimo {AIRTIME_MIN} MZN):")
        elif len(parts) == 3:
            amount = safe_int(parts[2])
            if amount is None or amount < AIRTIME_MIN:
                return con(f"Valor inválido. Mínimo {AIRTIME_MIN} MZN. Digite novamente:")
            if user.balance < amount:
                return end("Saldo insuficiente.")
            user.balance -= float(amount)
            db.add(user)
            tx = Tx(
                ref=f"AIR-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.TRANSFER,
                from_user_id=user.id,
                to_user_id=None,
                amount=float(amount),
                meta="airtime",
                status="OK",
            )
            db.add(tx)
            db.commit()
            return end(f"Crédito comprado: {amount} MZN. {balance_line(user)}")

    # fallback
    return main_menu()