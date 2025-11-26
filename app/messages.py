from datetime import datetime

SUPORTE = "Se tiver dúvidas, ligue para +258 84 966 6964."

def format_datetime():
    agora = datetime.now()
    semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo"
    ]
    return f"{semana[agora.weekday()]}, {agora.strftime('%d/%m/%Y %H:%M:%S')}"

def fmt(valor: float):
    return f"{valor:,.2f} MT".replace(",", " ").replace(".", ",")


# ---------------------- TRANSFERÊNCIA ----------------------
def msg_transfer_sender(nome_dest, num_dest, valor, txid):
    return (
        f"✔️ Transferência enviada com sucesso\n\n"
        f"Destinatário: {nome_dest} ({num_dest})\n"
        f"Valor enviado: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Operação registada.\n{SUPORTE}"
    )

def msg_transfer_receiver(nome_origem, num_origem, valor, txid):
    return (
        f"📩 Recebeu dinheiro na sua conta A-Taku\n\n"
        f"Origem: {nome_origem} ({num_origem})\n"
        f"Valor recebido: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Valor disponível no seu saldo.\n{SUPORTE}"
    )


# ---------------------- DEPÓSITO VIA AGENTE ----------------------
def msg_deposit_customer(agent_name, agent_code, valor, txid):
    return (
        f"💰 Depósito confirmado na sua conta\n\n"
        f"Agente: {agent_name} ({agent_code})\n"
        f"Valor depositado: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Saldo atualizado.\n{SUPORTE}"
    )

def msg_deposit_agent(cliente_num, valor, txid):
    return (
        f"🧾 Operação de depósito efectuada\n\n"
        f"Cliente: {cliente_num}\n"
        f"Valor: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Operação registada.\n{SUPORTE}"
    )


# ---------------------- CASHOUT / LEVANTAMENTO ----------------------
def msg_cashout_customer(agent_name, agent_code, valor, txid):
    return (
        f"🏧 Levantamento efectuado com sucesso\n\n"
        f"Agente: {agent_name} ({agent_code})\n"
        f"Valor levantado: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Dinheiro entregue.\n{SUPORTE}"
    )

def msg_cashout_agent(cliente_num, valor, txid):
    return (
        f"🧾 Cliente efectuou levantamento\n\n"
        f"Cliente: {cliente_num}\n"
        f"Valor: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Registado no seu terminal.\n{SUPORTE}"
    )


# ---------------------- PAGAMENTO DE SERVIÇO ----------------------
def msg_service_payment(cliente_num, servico_nome, valor, txid):
    return (
        f"🧾 Pagamento de serviço concluído\n\n"
        f"Serviço: {servico_nome}\n"
        f"Valor pago: {fmt(valor)}\n"
        f"Conta: {cliente_num}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Obrigado por usar.\n{SUPORTE}"
    )


# ---------------------- PAGAMENTO EM LOJA (MERCHANT) ----------------------
def msg_merchant_payment(loja_nome, valor, txid):
    return (
        f"🛒 Pagamento efectuado na loja\n\n"
        f"Loja: {loja_nome}\n"
        f"Valor pago: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Compra finalizada.\n{SUPORTE}"
    )

def msg_merchant_receive(cliente_nome, valor, txid):
    return (
        f"🧾 Venda registada\n\n"
        f"Recebeu {fmt(valor)} de {cliente_nome}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Valor disponível na sua conta.\n{SUPORTE}"
    )


# ---------------------- REVERSÃO ----------------------
def msg_reversal_sender(valor, txid):
    return (
        f"🔄 Reversão concluída\n\n"
        f"Valor devolvido: {fmt(valor)}\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku — Montante retornou ao seu saldo.\n{SUPORTE}"
    )

def msg_reversal_receiver(valor, txid):
    return (
        f"⚠️ Reversão efectuada\n\n"
        f"O valor de {fmt(valor)} que tinha recebido foi revertido.\n"
        f"TXID: {txid}\n\n"
        f"Data e hora:\n{format_datetime()}\n\n"
        f"A-Taku.\n{SUPORTE}"
    )