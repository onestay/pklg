from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class ProductResult(BaseModel):
    description: str
    detailed_description: str
    manufacturer: str
    mpn: str
    datasheet_url: str
    product_url: str
    component_type: str | None = None
    package: str | None = None
    value_number: Decimal | None = None
    value_prefix: str | None = None


class Distributor(Protocol):
    interactive: bool

    def query(self, part_number: str) -> ProductResult: ...


def create_distributor(
    name: str, config: dict, component_type: str | None = None
) -> Distributor:
    if name == "digikey":
        from .digikey import DigiKey

        dk_cfg = config.get("digikey")
        if not dk_cfg:
            raise ValueError("[digikey] not configured in pklg.toml")
        return DigiKey(dk_cfg["client_id"], dk_cfg["client_secret"])
    if name == "manual":
        from .manual import Manual

        return Manual(component_type)
    raise ValueError(f"Unknown distributor: {name}")
