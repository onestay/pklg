import re
from decimal import Decimal

PREFIX_MULTIPLIERS: dict[str, Decimal] = {
    "p": Decimal("1e-12"),
    "n": Decimal("1e-9"),
    "u": Decimal("1e-6"),
    "m": Decimal("1e-3"),
    "": Decimal("1"),
    "k": Decimal("1e3"),
    "M": Decimal("1e6"),
}

# Per component type, which prefixes to prefer (ordered small → large)
PREFERRED_PREFIXES: dict[str, list[str]] = {
    "capacitor": ["p", "n", "u"],
    "resistor": ["", "k", "M"],
    "inductor": ["n", "u", "m"],
}


def format_short_value(number: Decimal, prefix: str, component_type: str) -> str:
    """Format an engineering value as a short string.

    Examples:
        format_short_value(Decimal("0.33"), "u", "capacitor") → "330n"
        format_short_value(Decimal("4.7"), "u", "capacitor") → "4u7"
        format_short_value(Decimal("10"), "k", "resistor") → "10k"
    """
    if prefix not in PREFIX_MULTIPLIERS:
        raise ValueError(f"Unknown prefix '{prefix}'")

    # Convert to base unit value
    base_value = number * PREFIX_MULTIPLIERS[prefix]

    # Pick the best prefix for this component type
    preferred = PREFERRED_PREFIXES.get(component_type)
    if not preferred:
        raise ValueError(f"Unknown component type '{component_type}'")

    best_prefix = preferred[-1]  # fallback to largest
    for p in preferred:
        scaled = base_value / PREFIX_MULTIPLIERS[p]
        if Decimal("1") <= scaled < Decimal("1000"):
            best_prefix = p
            break

    scaled = base_value / PREFIX_MULTIPLIERS[best_prefix]

    # Remove trailing zeros for clean display
    scaled = scaled.normalize()

    # Format: use prefix as decimal separator if there's a fractional part
    if scaled == scaled.to_integral_value():
        # Whole number: "330n", "10k", "100p"
        result = f"{int(scaled)}{best_prefix}"
    else:
        # Fractional: use prefix as decimal separator "4u7", "2n2"
        int_part = int(scaled)
        frac_part = scaled - int_part
        # Get fractional digits without leading "0."
        frac_str = str(frac_part.normalize())[2:]
        result = f"{int_part}{best_prefix}{frac_str}"

    return result


def parse_short_value(text: str) -> tuple[Decimal, str]:
    """Parse an EE short notation value into (number, prefix).

    Examples:
        parse_short_value("100n") → (Decimal("100"), "n")
        parse_short_value("4u7") → (Decimal("4.7"), "u")
        parse_short_value("10k") → (Decimal("10"), "k")
        parse_short_value("47") → (Decimal("47"), "")
    """
    text = text.strip()
    # "4u7" pattern: digits, prefix, digits
    m = re.match(r"^(\d+)([pnumkMG])(\d+)$", text)
    if m:
        return Decimal(f"{m.group(1)}.{m.group(3)}"), m.group(2)
    # "100n" or "4.7u" pattern: number then prefix
    m = re.match(r"^(\d+\.?\d*)([pnumkMG])$", text)
    if m:
        return Decimal(m.group(1)), m.group(2)
    # Bare number "47"
    m = re.match(r"^(\d+\.?\d*)$", text)
    if m:
        return Decimal(m.group(1)), ""
    raise ValueError(f"Cannot parse short value from '{text}'")
