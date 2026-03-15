import json
from decimal import Decimal
from pathlib import Path

import pytest

from pklg.distributors.digikey import (
    DigiKeyProduct,
    detect_component_type,
    extract_value_text,
    parse_package_code,
    parse_product,
    parse_value,
    to_product_result,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# --- parse_package_code ---


class TestParsePackageCode:
    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("0805 (2012 Metric)", "0805"),
            ("0603 (1608 Metric)", "0603"),
            ("1206 (3216 Metric)", "1206"),
            ("0402 (1005 Metric)", "0402"),
            ("0201 (0603 Metric)", "0201"),
        ],
    )
    def test_valid(self, input_str, expected):
        assert parse_package_code(input_str) == expected

    def test_invalid(self):
        with pytest.raises(ValueError, match="Cannot parse package code"):
            parse_package_code("SOP-8")

    def test_nonstandard(self):
        with pytest.raises(ValueError, match="Cannot parse package code"):
            parse_package_code("Nonstandard")


# --- parse_value ---


class TestParseValue:
    @pytest.mark.parametrize(
        "input_str,expected_number,expected_prefix",
        [
            ("0.33 µF", Decimal("0.33"), "u"),
            ("10 kOhms", Decimal("10"), "k"),
            ("4.7 µH", Decimal("4.7"), "u"),
            ("100 pF", Decimal("100"), "p"),
            ("47 Ohms", Decimal("47"), ""),
            ("1 MOhms", Decimal("1"), "M"),
            ("22 nF", Decimal("22"), "n"),
            ("2.2 mH", Decimal("2.2"), "m"),
        ],
    )
    def test_valid(self, input_str, expected_number, expected_prefix):
        number, prefix = parse_value(input_str)
        assert number == expected_number
        assert prefix == expected_prefix

    def test_unknown_unit(self):
        with pytest.raises(ValueError, match="Unknown unit"):
            parse_value("10 flarps")

    def test_unparseable(self):
        with pytest.raises(ValueError, match="Cannot parse value"):
            parse_value("abc")


# --- detect_component_type ---


class TestDetectComponentType:
    @pytest.mark.parametrize(
        "category,expected",
        [
            ("Capacitors", "capacitor"),
            ("Resistors", "resistor"),
            ("Inductors, Coils, Chokes", "inductor"),
            ("RF and Wireless", None),
            ("Connectors", None),
        ],
    )
    def test_detection(self, category, expected):
        product = DigiKeyProduct(
            description="",
            detailed_description="",
            manufacturer="",
            mpn="",
            datasheet_url="",
            product_url="",
            category=category,
            subcategory="",
            parameters={},
        )
        assert detect_component_type(product) == expected


# --- parse_product with real fixtures ---


class TestParseProduct:
    def test_capacitor(self):
        raw = _load_fixture("digikey_capacitor.json")
        product = parse_product(raw)
        assert product.mpn == "CL21B334KBFNNNE"
        assert product.manufacturer == "Samsung Electro-Mechanics"
        assert product.description == "CAP CER 0.33UF 50V X7R 0805"
        assert "0.33 µF" in product.detailed_description
        assert product.category == "Capacitors"
        assert product.subcategory == "Ceramic Capacitors"
        assert product.parameters["Capacitance"] == "0.33 µF"
        assert product.parameters["Package / Case"] == "0805 (2012 Metric)"
        assert product.datasheet_url.startswith("https://")
        assert not product.datasheet_url.startswith("//")

    def test_resistor(self):
        raw = _load_fixture("digikey_resistor.json")
        product = parse_product(raw)
        assert product.mpn == "RC1005F103CS"
        assert product.manufacturer == "Samsung Electro-Mechanics"
        assert product.description == "RES SMD 10K OHM 1% 1/16W 0402"
        assert product.category == "Resistors"
        assert product.parameters["Resistance"] == "10 kOhms"
        assert product.parameters["Package / Case"] == "0402 (1005 Metric)"

    def test_inductor(self):
        raw = _load_fixture("digikey_inductor.json")
        product = parse_product(raw)
        assert product.mpn == "NRS5030T330MMGJV"
        assert product.manufacturer == "Taiyo Yuden"
        assert product.description == "FIXED IND 33UH 800MA 292.5 MOHM"
        assert product.category == "Inductors, Coils, Chokes"
        assert product.parameters["Inductance"] == "33 µH"
        assert product.parameters["Package / Case"] == "Nonstandard"

    def test_inner_dict_directly(self):
        """parse_product works when given the inner Product dict directly."""
        raw = _load_fixture("digikey_resistor.json")
        inner = raw["Product"]
        product = parse_product(inner)
        assert product.mpn == "RC1005F103CS"
        assert product.manufacturer == "Samsung Electro-Mechanics"


# --- to_product_result ---


class TestToProductResult:
    def test_capacitor(self):
        raw = _load_fixture("digikey_capacitor.json")
        product = parse_product(raw)
        result = to_product_result(product)
        assert result.component_type == "capacitor"
        assert result.package == "0805"
        assert result.value_number == Decimal("0.33")
        assert result.value_prefix == "u"
        assert result.mpn == "CL21B334KBFNNNE"
        assert result.manufacturer == "Samsung Electro-Mechanics"

    def test_resistor(self):
        raw = _load_fixture("digikey_resistor.json")
        product = parse_product(raw)
        result = to_product_result(product)
        assert result.component_type == "resistor"
        assert result.package == "0402"
        assert result.value_number == Decimal("10")
        assert result.value_prefix == "k"

    def test_inductor(self):
        raw = _load_fixture("digikey_inductor.json")
        product = parse_product(raw)
        result = to_product_result(product)
        assert result.component_type == "inductor"
        assert result.package is None  # "Nonstandard" doesn't parse
        assert result.value_number == Decimal("33")
        assert result.value_prefix == "u"

    def test_unknown_category(self):
        product = DigiKeyProduct(
            description="Some connector",
            detailed_description="A USB connector",
            manufacturer="Molex",
            mpn="123456",
            datasheet_url="https://example.com/ds.pdf",
            product_url="https://example.com/product",
            category="Connectors",
            subcategory="USB",
            parameters={},
        )
        result = to_product_result(product)
        assert result.component_type is None
        assert result.package is None
        assert result.value_number is None
        assert result.value_prefix is None
        assert result.manufacturer == "Molex"
        assert result.mpn == "123456"


# --- Full pipeline tests ---


class TestFullPipeline:
    def test_capacitor_pipeline(self):
        raw = _load_fixture("digikey_capacitor.json")
        product = parse_product(raw)
        assert detect_component_type(product) == "capacitor"
        value_text = extract_value_text(product, "capacitor")
        assert value_text == "0.33 µF"
        number, prefix = parse_value(value_text)
        assert number == Decimal("0.33")
        assert prefix == "u"
        assert parse_package_code(product.parameters["Package / Case"]) == "0805"

    def test_resistor_pipeline(self):
        raw = _load_fixture("digikey_resistor.json")
        product = parse_product(raw)
        assert detect_component_type(product) == "resistor"
        value_text = extract_value_text(product, "resistor")
        assert value_text == "10 kOhms"
        number, prefix = parse_value(value_text)
        assert number == Decimal("10")
        assert prefix == "k"
        assert parse_package_code(product.parameters["Package / Case"]) == "0402"

    def test_inductor_pipeline(self):
        raw = _load_fixture("digikey_inductor.json")
        product = parse_product(raw)
        assert detect_component_type(product) == "inductor"
        value_text = extract_value_text(product, "inductor")
        assert value_text == "33 µH"
        number, prefix = parse_value(value_text)
        assert number == Decimal("33")
        assert prefix == "u"

    def test_inductor_nonstandard_package(self):
        """Inductor with 'Nonstandard' package — parse_package_code should raise."""
        raw = _load_fixture("digikey_inductor.json")
        product = parse_product(raw)
        with pytest.raises(ValueError):
            parse_package_code(product.parameters["Package / Case"])
