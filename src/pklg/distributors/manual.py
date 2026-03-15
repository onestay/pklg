import questionary

from . import ProductResult

SPECIALIZED_TYPES = {"capacitor", "resistor", "inductor"}


class Manual:
    interactive = True

    def __init__(self, component_type: str | None):
        self.component_type = component_type

    def query(self, part_number: str) -> ProductResult:
        manufacturer = questionary.text("Manufacturer:").unsafe_ask()
        mpn = questionary.text("MPN:").unsafe_ask()
        description = questionary.text("Description:").unsafe_ask()
        datasheet_url = questionary.text("Datasheet URL:", default="").unsafe_ask()
        product_url = questionary.text("Product URL:", default="").unsafe_ask()
        package = questionary.text("Package (e.g. 0805):", default="").unsafe_ask()

        return ProductResult(
            description=description,
            detailed_description=description,
            manufacturer=manufacturer,
            mpn=mpn,
            datasheet_url=datasheet_url,
            product_url=product_url,
            component_type=self.component_type if self.component_type != "generic" else None,
            package=package or None,
        )
