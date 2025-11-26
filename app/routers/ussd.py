from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import User, Tx, TxType
from ..utils import normalize_phone
from ..auth import verify_password, hash_password
from ..wallet_advanced import make_transfer, calc_cashout_fee

router = APIRouter(tags=["USSD"])

INITIAL_BONUS = 25.0
DEFAULT_PIN = "0000"
AIRTIME_MIN = 20


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


def require_pin_change(user: User) -> bool:
    return verify_password(DEFAULT_PIN, user.pin_hash)


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

    parts = [p for p in text.split("*") if p] if text else []

    if not parts:
        return main_menu()

    # 1) Criar conta
    if parts[0] == "1":
        if require_pin_change(user):
            if len(parts) == 1:
                return con("Crie seu PIN (4 dígitos):")
            if len(parts) == 2:
                new_pin = parts[1]
                if not new_pin.isdigit() or len(new_pin) != 4 or new_pin == DEFAULT_PIN:
                    return con("PIN inválido. Tente de novo:")
                user.pin_hash = hash_password(new_pin)
                db.commit()
                return end("Conta ativada com sucesso.")
        return end("Conta já existe. Use Entrar.")

    # 2) Login (com ajuste para definir PIN se ainda é o default)
    if parts[0] == "2":
        if require_pin_change(user):
            if len(parts) == 1:
                return con("Defina novo PIN (4 dígitos):")
            if len(parts) == 2:
                new_pin = parts[1]
                if not new_pin.isdigit() or len(new_pin) != 4 or new_pin == DEFAULT_PIN:
                    return con("PIN inválido. Tente de novo:")
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
        if len(parts) == 2:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            return end(f"Saldo atual: {user.balance:.2f} MZN")

    # 4) Transferência
    if parts[0] == "4":
        if len(parts) == 1:
            return con("Digite PIN:")
        if len(parts) == 2:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            return con("Digite número do destinatário:")
        if len(parts) == 3:
            return con("Digite o valor:")
        if len(parts) == 4:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            try:
                recipient = normalize_phone(parts[2])
            except Exception:
                return end("Telefone destino inválido.")
            try:
                amount = float(parts[3].strip())
            except Exception:
                return end("Valor inválido.")
            ok, msg = make_transfer(db, user.phone, recipient, amount, pin)
            return end(msg)

    # 5) Cashout
    if parts[0] == "5":
        if len(parts) == 1:
            return con("Digite PIN:")
        if len(parts) == 2:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            return con("Digite valor a levantar:")
        if len(parts) == 3:
            try:
                amount = float(parts[2].strip())
            except ValueError:
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
            return end(
                f"Levantou {amount:.2f} MZN. Taxa: {fee:.2f}. Saldo: {user.balance:.2f}"
            )

    # 6) Pagar serviços (agora com PIN)
    if parts[0] == "6":
        if len(parts) == 1:
            return con("Digite PIN:")
        if len(parts) == 2:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            return con("Digite referência do serviço:")
        if len(parts) == 3:
            return con("Digite o valor:")
        if len(parts) == 4:
            pin = parts[1]
            if not verify_password(pin, user.pin_hash):
                return end("PIN inválido.")
            ref = parts[2]
            try:
                amount = float(parts[3].strip())
            except Exception:
                return end("Valor inválido.")
            if user.balance < amount:
                return end("Saldo insuficiente.")
            user.balance -= amount
            db.commit()
            tx = Tx(
                ref=f"PAY-{int(datetime.utcnow().timestamp())}-{user.id}",
                type=TxType.TRANSFER,
                from_user_id=user.id,
                to_user_id=None,
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
        if len(parts) == 1:
            return con(f"Digite valor mínimo {AIRTIME_MIN}:")
        if len(parts) == 2:
            try:
                amount = float(parts[1].strip())
            except Exception:
                return end("Valor inválido.")
            if amount < AIRTIME_MIN:
                return end(f"Valor mínimo é {AIRTIME_MIN}.")
            if user.balance < amount:
                return end("Saldo insuficiente.")
            user.balance -= amount
            db.commit()
            return end(f"Crédito comprado: {amount:.2f} MZN")

    return main_menu()