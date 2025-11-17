import phonenumbers

def normalize_phone(raw: str, default_region: str = "MZ") -> str:
    raw = (raw or "").strip()
    try:
        num = phonenumbers.parse(raw, default_region)
        if not phonenumbers.is_valid_number(num):
            raise ValueError("invalid")
        return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        digits = ''.join(ch for ch in raw if ch.isdigit() or ch == '+')
        if not digits:
            raise
        return digits
