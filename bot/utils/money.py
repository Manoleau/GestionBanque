def parse_amount_to_cents(amount_str: str) -> int:
    """Convertit une chaîne de montant ("12.34" ou "12,34") en centimes entiers.
    Lève ValueError si conversion impossible.
    """
    normalized = amount_str.replace(",", ".").strip()
    value = round(float(normalized) * 100)
    return int(value)


def format_cents(cents: int) -> str:
    """Formate un entier en centimes vers une chaîne lisible (ex: 1234 -> "12.34€")."""
    sign = '-' if cents < 0 else ''
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}€"
