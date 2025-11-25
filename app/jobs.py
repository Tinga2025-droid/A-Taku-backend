# app/jobs.py
from datetime import datetime
from sqlalchemy.orm import Session

from .models_advanced import AgentCommission
from .models import User, Tx, TxType


def process_agent_commissions(db: Session) -> dict:
    """
    Paga todas as comissões de agentes que:
    - ainda não foram pagas (paid = False)
    - já passaram da payable_date (D+30)

    A comissão é creditada no saldo do agente (balance).
    Também registra um Tx de COMMISSION_PAY.
    """
    now = datetime.utcnow()

    pending = db.query(AgentCommission).filter(
        AgentCommission.paid == False,  # noqa: E712
        AgentCommission.payable_date <= now,
    ).all()

    total_agents = 0
    total_amount = 0.0

    for c in pending:
        agent = db.query(User).filter(User.id == c.agent_id).first()
        if not agent:
            # agente apagado ou inconsistente, marca como pago para não travar loop
            c.paid = True
            continue

        agent.balance += c.amount
        c.paid = True

        tx = Tx(
            ref=f"AGTCOM-{c.id}",
            type=TxType.COMMISSION,
            from_user_id=None,
            to_user_id=agent.id,
            amount=c.amount,
            meta="agent_commission_payout",
            status="OK",
        )
        db.add(tx)

        total_agents += 1
        total_amount += c.amount

    db.commit()

    return {
        "processed_commissions": len(pending),
        "agents_affected": total_agents,
        "total_paid": total_amount,
    }