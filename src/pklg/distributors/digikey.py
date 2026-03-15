import re
import sys
from decimal import Decimal

from httpx import Client
from pydantic import BaseModel

from . import ProductResult


class DigiKeyProduct(BaseModel):
    description: str
    detailed_description: str
    manufacturer: str
    mpn: str
    datasheet_url: str
    product_url: str
    category: str
    subcategory: str
    parameters: dict[str, str]


# DigiKey parameter names that hold the main value per component type
DIGIKEY_VALUE_PARAMS: dict[str, str] = {
    "capacitor": "Capacitance",
    "resistor": "Resistance",
    "inductor": "Inductance",
}

# DigiKey category name substrings → component type
DIGIKEY_CATEGORY_HINTS: dict[str, str] = {
    "Capacitors": "capacitor",
    "Resistors": "resistor",
    "Inductors": "inductor",
}

# DigiKey unit strings → SI prefix
UNIT_ALIASES: dict[str, str] = {
    "µF": "u",
    "pF": "p",
    "nF": "n",
    "F": "",
    "kOhms": "k",
    "Ohms": "",
    "MOhms": "M",
    "µH": "u",
    "nH": "n",
    "mH": "m",
    "H": "",
}


def parse_product(raw: dict) -> DigiKeyProduct:
    """Parse raw DigiKey API JSON into a structured product."""
    # v4 API wraps product data under a "Product" key
    product = raw.get("Product", raw)
    desc = product.get("Description", {})

    # Extract parameters as flat dict
    parameters: dict[str, str] = {}
    for param in product.get("Parameters", []):
        key = param.get("ParameterText", "")
        value = param.get("ValueText", "")
        if key and value:
            parameters[key] = value

    # Normalize datasheet URL
    datasheet_url = product.get("DatasheetUrl", "") or ""
    if datasheet_url.startswith("//"):
        datasheet_url = "https:" + datasheet_url

    # Subcategory
    child_cats = product.get("Category", {}).get("ChildCategories", [])
    subcategory = child_cats[0].get("Name", "") if child_cats else ""

    result = DigiKeyProduct(
        description=desc.get("ProductDescription", ""),
        detailed_description=desc.get("DetailedDescription", ""),
        manufacturer=product.get("Manufacturer", {}).get("Name", ""),
        mpn=product.get("ManufacturerProductNumber", ""),
        datasheet_url=datasheet_url,
        product_url=product.get("ProductUrl", ""),
        category=product.get("Category", {}).get("Name", ""),
        subcategory=subcategory,
        parameters=parameters,
    )

    if not result.mpn:
        keys = list(product.keys())[:10]
        print(f"Warning: 'ManufacturerProductNumber' not found. Available keys: {keys}", file=sys.stderr)
    if not result.manufacturer:
        keys = list(product.get("Manufacturer", {}).keys())
        print(f"Warning: 'Manufacturer.Name' not found. Available keys: {keys}", file=sys.stderr)

    return result


def parse_package_code(package_case: str) -> str:
    """Extract imperial package code from DigiKey's format.

    "0805 (2012 Metric)" → "0805"
    """
    match = re.match(r"^(\d{4})\b", package_case.strip())
    if not match:
        raise ValueError(f"Cannot parse package code from '{package_case}'")
    return match.group(1)


def parse_value(value_text: str) -> tuple[Decimal, str]:
    """Parse a DigiKey value string into (number, SI prefix).

    "0.33 µF" → (Decimal("0.33"), "u")
    "10 kOhms" → (Decimal("10"), "k")
    """
    value_text = value_text.strip()
    match = re.match(r"^([\d.]+)\s*(.+)$", value_text)
    if not match:
        raise ValueError(f"Cannot parse value from '{value_text}'")

    number = Decimal(match.group(1))
    unit_str = match.group(2).strip()

    prefix = UNIT_ALIASES.get(unit_str)
    if prefix is None:
        raise ValueError(f"Unknown unit '{unit_str}' in '{value_text}'")

    return number, prefix


def detect_component_type(product: DigiKeyProduct) -> str | None:
    """Detect component type from DigiKey category name."""
    for hint, comp_type in DIGIKEY_CATEGORY_HINTS.items():
        if hint in product.category:
            return comp_type
    return None


def extract_value_text(product: DigiKeyProduct, component_type: str) -> str | None:
    """Get the raw value parameter text for a component type."""
    param_name = DIGIKEY_VALUE_PARAMS.get(component_type)
    if not param_name:
        return None
    return product.parameters.get(param_name)


def to_product_result(product: DigiKeyProduct) -> ProductResult:
    """Convert a DigiKey-specific product to a generic ProductResult."""
    comp_type = detect_component_type(product)

    package = None
    package_case = product.parameters.get("Package / Case", "")
    try:
        package = parse_package_code(package_case)
    except ValueError:
        pass

    value_number = None
    value_prefix = None
    if comp_type:
        raw_value = extract_value_text(product, comp_type)
        if raw_value:
            try:
                value_number, value_prefix = parse_value(raw_value)
            except ValueError:
                pass

    return ProductResult(
        description=product.description,
        detailed_description=product.detailed_description,
        manufacturer=product.manufacturer,
        mpn=product.mpn,
        datasheet_url=product.datasheet_url,
        product_url=product.product_url,
        component_type=comp_type,
        package=package,
        value_number=value_number,
        value_prefix=value_prefix,
    )


class DigiKey:
    interactive = False

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_endpoint = "https://api.digikey.com/v1/oauth2/token"

    def get_token(self, client: Client) -> str:
        resp = client.post(
            self.token_endpoint,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )

        resp.raise_for_status()

        return resp.json()["access_token"]

    def query(self, part_number: str) -> ProductResult:
        with Client() as client:
            token = self.get_token(client)
            headers = {
                "X-DIGIKEY-Locale-Language": "en",
                "X-DIGIKEY-Locale-Currency": "EUR",
                "X-DIGIKEY-Locale-Site": "DE",
                "X-DIGIKEY-Client-Id": self.client_id,
                "Authorization": f"Bearer {token}",
            }

            resp = client.get(
                f"https://api.digikey.com/products/v4/search/{part_number}/productdetails",
                headers=headers,
            )

            resp.raise_for_status()

            return to_product_result(parse_product(resp.json()))
