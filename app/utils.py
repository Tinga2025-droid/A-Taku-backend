import phonenumbers


def normalize_phone(raw: str, default_region: str = "MZ") -> str:
    """
    Normaliza números para formato E.164.

    Exemplos:
    - "849001234"      -> "+258849001234"
    - "+258849001234"  -> "+258849001234"
    - "00258849001234" -> "+258849001234"
    """
    raw = (raw or "").strip()

    # Tentativa principal com phonenumbers
    try:
        num = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    # Fallback: apenas dígitos
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise ValueError("Telefone inválido")

    # Formatos comuns em Moçambique
    if digits.startswith("258"):
        candidate = "+" + digits
    elif len(digits) == 9 and digits.startswith(("82", "83", "84", "85", "86", "87")):
        candidate = "+258" + digits
    else:
        candidate = "+" + digits

    try:
        num = phonenumbers.parse(candidate, default_region)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        pass

    raise ValueError("Telefone inválido ou não suportado")
