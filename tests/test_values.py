from decimal import Decimal

import pytest

from pklg.values import format_short_value, parse_short_value


@pytest.mark.parametrize(
    "number,prefix,component_type,expected",
    [
        # Capacitor values
        (Decimal("0.33"), "u", "capacitor", "330n"),
        (Decimal("4.7"), "u", "capacitor", "4u7"),
        (Decimal("100"), "p", "capacitor", "100p"),
        (Decimal("1"), "u", "capacitor", "1u"),
        (Decimal("10"), "n", "capacitor", "10n"),
        (Decimal("2.2"), "n", "capacitor", "2n2"),
        # Resistor values
        (Decimal("10"), "k", "resistor", "10k"),
        (Decimal("4.7"), "k", "resistor", "4k7"),
        (Decimal("100"), "", "resistor", "100"),
        (Decimal("1"), "M", "resistor", "1M"),
        (Decimal("47"), "", "resistor", "47"),
        # Inductor values
        (Decimal("10"), "u", "inductor", "10u"),
        (Decimal("4.7"), "u", "inductor", "4u7"),
        (Decimal("100"), "n", "inductor", "100n"),
        (Decimal("2.2"), "m", "inductor", "2m2"),
    ],
)
def test_format_short_value(number, prefix, component_type, expected):
    assert format_short_value(number, prefix, component_type) == expected


def test_unknown_prefix():
    with pytest.raises(ValueError, match="Unknown prefix"):
        format_short_value(Decimal("1"), "X", "capacitor")


def test_unknown_component_type():
    with pytest.raises(ValueError, match="Unknown component type"):
        format_short_value(Decimal("1"), "u", "transistor")


@pytest.mark.parametrize(
    "text,expected_number,expected_prefix",
    [
        ("100n", Decimal("100"), "n"),
        ("4u7", Decimal("4.7"), "u"),
        ("10k", Decimal("10"), "k"),
        ("47", Decimal("47"), ""),
        ("2n2", Decimal("2.2"), "n"),
        ("1M", Decimal("1"), "M"),
        ("4.7u", Decimal("4.7"), "u"),
        ("330p", Decimal("330"), "p"),
        ("100", Decimal("100"), ""),
        ("  10k  ", Decimal("10"), "k"),
    ],
)
def test_parse_short_value(text, expected_number, expected_prefix):
    number, prefix = parse_short_value(text)
    assert number == expected_number
    assert prefix == expected_prefix


def test_parse_short_value_invalid():
    with pytest.raises(ValueError, match="Cannot parse short value"):
        parse_short_value("abc")
