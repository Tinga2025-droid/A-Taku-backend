from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Tx, TxType
from ..utils import normalize_phone
from ..auth import verify_password, hash_password
from ..wallet_advanced import make_transfer, calc_cashout_fee

router = APIRouter(tags=["USSD"])

INITIAL_BONUS = 25.0
DEFAULT_PIN = "0000"
AIRTIME_MIN = 20


# -------------------------------
# 🛡️  PIN FORTE
# -------------------------------
WEAK_PINS = {"0000", "1111", "1234", "2222", "3333", "4444",
             "5555", "6666", "7777", "8888", "9999", "4321"}

def is_weak_pin(pin: str) -> bool:
    return (pin in WEAK_PINS) or (not pin.isdigit()) or (len(pin) != 4)


# -------------------------------
# 🔐 Bloqueio de operações com PIN default
# -------------------------------
def must_change_pin(user: User) -> bool:
    return verify_password(DEFAULT_PIN, user.pin_hash)


# -------------------------------
# 🛡️ Anti-spam básico USSD
# (não quebra nada / sem Redis)
# -------------------------------
def anti_spam(user: User) -> bool:
    now = datetime.utcnow()
    if user.last_tx_at and (now - user.last_tx_at).total_seconds() < 1:
        return False
    user.last_tx_at = now
    return True


def end(text: str) -> str:
    return f"END {text}"


def con(text: str) -> str:
    return f"CON {text}"


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
        pin_hash=hash_password(DEFAULT_PIN),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    tx = Tx(
        ref=f"BONUS-{int(datetime.utcnow().timestamp())}-{user.id}",
        type=TxType.DEPOSIT,
        to_user_id=user.id,
        amount=INITIAL_BONUS,
        meta="Bônus de boas-vindas via USSD",
        status="OK",
    )
    db.add(tx)
    db.commit()

    return user


def main_menu() -> str:
    return con(
        "Bem-vindo ao A-Taku\n"
        "1. Criar conta\n"
        "2. Entrar\n"
        "3. Ver saldo\n"
        "4. Transferir dinheiro\n"
        "5. Levantar (cashout)\n"
        "6. Pagar serviços\n"
        "7. Extrato\n"
        "8. Comprar crédito"
    )


@router.post("/ussd", response_class=PlainTextResponse)
def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    db: Session = Depends(get_db),
):
    try:
        phone = normalize_phone(phoneNumber)
    except Exception:
        return end("Telefone inválido ou não suportado.")

    user = get_or_create_user(db, phone)

    # Anti-spam: 1 ação por segundo
    if not anti_spam(user):
        db.commit()
        return end("Operações muito rápidas. Tente novamente.")

    parts = [p for p in text.split("*") if p] if text else []

    if not parts:
        return main_menu()

    # 1) Criar conta
    if parts[0] == "1":
        if must_change_pin(user):
            if len(parts) == 1:
                return con("Crie seu PIN (4 dígitos):")
            if len(parts) == 2:
                new_pin = parts[1]
                if is_weak_pin(new_pin):
                    return con("PIN fraco ou inválido. Tente outro:")
                user.pin_hash = hash_password(new_pin)
                db.commit()
                return end("Conta ativada com sucesso.")
        return end("Conta já existe. Use Entrar.")

    # 2) Login / Definir PIN se default
    if parts[0] == "2":
        if must_change_pin(user):
            if len(parts) == 1:
                return con("Defina novo PIN (4 dígitos):")
            if len(parts) == 2:
                new_pin = parts[1]
                if is_weak_pin(new_pin):
                    return con("PIN fraco. Escolha outro:")
                user.pin_hash = hash_password(new_pin)
                db.commit()
                return end("PIN definido com sucesso. Use Entrar novamente.")
        if len(parts) == 1:
            return con("Digite seu PIN:")
        if len(parts) == 2:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            return end(f"Login OK. Saldo: {user.balance:.2f} MZN")

    # 3) Saldo
    if parts[0] == "3":
        if len(parts) == 1:
            return con("Digite PIN:")
        pin = parts[1]
        if not verify_password(pin, user.pin_hash):
            return end("PIN inválido.")
        return end(f"Saldo atual: {user.balance:.2f} MZN")

    # 4) Transferência
    if parts[0] == "4":
        # PIN default é proibido transferir
        if must_change_pin(user):
            return end("Defina seu PIN antes de transferir (menu Criar Conta).")

        if len(parts) == 1:
            return con("Digite PIN:")
        pin = parts[1]
        if not verify_password(pin, user.pin_hash):
            return end("PIN inválido.")

        if len(parts) == 2:
            return con("Digite número do destinatário:")
        if len(parts) == 3:
            return con("Digite o valor:")
        if len(parts) == 4:
            try:
                recipient = normalize_phone(parts[2])
                amount = float(parts[3].strip())
            except:
                return end("Dados inválidos.")

            ok, msg = make_transfer(db, user.phone, recipient, amount, pin)
            return end(msg)

    # 5) Cashout
    if parts[0] == "5":
        if must_change_pin(user):
            return end("Defina PIN antes de levantar valores.")

        if len(parts) == 1:
            return con("Digite PIN:")
        pin = parts[1]
        if not verify_password(pin, user.pin_hash):
            return end("PIN inválido.")

        if len(parts) == 2:
            return con("Digite valor a levantar:")
        if len(parts) == 3:
            try:
                amount = float(parts[2].strip())
            except:
                return end("Valor inválido.")

            fee = calc_cashout_fee(amount)
            if fee is None:
                return end("Valor fora das faixas permitidas.")

            total = amount + fee
            if user.balance < total:
                return end("Saldo insuficiente.")

            user.balance -= total
            db.commit()

            tx = Tx(
                ref=f"CASH-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.CASHOUT,
                from_user_id=user.id,
                amount=amount,
                meta=f"Taxa={fee:.2f}",
                status="OK",
            )
            db.add(tx)
            db.commit()

            return end(f"Levantou {amount:.2f} MZN. Taxa: {fee:.2f}. Saldo: {user.balance:.2f}")

    # 6) Pagamento
    if parts[0] == "6":
        if must_change_pin(user):
            return end("Defina PIN antes de pagar serviços.")

        if len(parts) == 1:
            return con("Digite PIN:")
        pin = parts[1]
        if not verify_password(pin, user.pin_hash):
            return end("PIN inválido.")

        if len(parts) == 2:
            return con("Digite referência do serviço:")
        if len(parts) == 3:
            return con("Digite o valor:")
        if len(parts) == 4:
            try:
                ref = parts[2]
                amount = float(parts[3].strip())
            except:
                return end("Valor inválido.")

            if user.balance < amount:
                return end("Saldo insuficiente.")

            user.balance -= amount
            db.commit()

            tx = Tx(
                ref=f"PAY-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.TRANSFER,
                from_user_id=user.id,
                amount=amount,
                meta=f"Pagamento servico ref={ref}",
                status="OK",
            )
            db.add(tx)
            db.commit()

            return end(f"Pagamento OK. Saldo: {user.balance:.2f} MZN")

    # 7) Extrato
    if parts[0] == "7":
        txs = (
            db.query(Tx)
            .filter((Tx.from_user_id == user.id) | (Tx.to_user_id == user.id))
            .order_by(Tx.created_at.desc())
            .limit(5)
            .all()
        )
        if not txs:
            return end("Sem movimentos.")
        lines = []
        for t in txs:
            direction = "OUT" if t.from_user_id == user.id else "IN"
            when = t.created_at.strftime("%d/%m %H:%M")
            lines.append(f"{when} {direction} {t.amount:.2f}")
        return end("\n".join(lines))

    # 8) Airtime
    if parts[0] == "8":
        if must_change_pin(user):
            return end("Defina PIN antes de comprar crédito.")

        if len(parts) == 1:
            return con(f"Digite valor mínimo {AIRTIME_MIN}:")
        if len(parts) == 2:
            try:
                amount = float(parts[1].strip())
            except:
                return end("Valor inválido.")

            if amount < AIRTIME_MIN:
                return end(f"Valor mínimo é {AIRTIME_MIN}.")
            if user.balance < amount:
                return end("Saldo insuficiente.")

            user.balance -= amount
            db.commit()
            return end(f"Crédito comprado: {amount:.2f} MZN")

    return main_menu()