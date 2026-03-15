import copy
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

# Add kicad-library-utils common/ to path for its internal imports (geometry, sexpr)
_kicad_lib_utils = Path(__file__).resolve().parents[2] / "lib" / "kicad-library-utils" / "common"
if str(_kicad_lib_utils) not in sys.path:
    sys.path.insert(0, str(_kicad_lib_utils))

from kicad_sym import KicadLibrary, Property


class PartInfo(BaseModel):
    """Identity and sourcing info common to all components."""

    name: str
    package: str
    manufacturer: str
    mpn: str
    datasheet: str
    description: str
    distributor_1_link: str
    distributor_1_part_number: str
    distributor_2_link: str = ""
    distributor_2_part_number: str = ""


@dataclass
class ComponentSpec:
    ref_des: str
    derive_from: str
    library_name: str
    source_library: str
    footprints: dict[str, str] = field(default_factory=dict)


COMPONENT_SPECS: dict[str, ComponentSpec] = {
    "capacitor": ComponentSpec(
        ref_des="C",
        derive_from="C",
        library_name="Capacitor",
        source_library="Device.kicad_sym",
        footprints={
            "0201": "Capacitor_SMD:C_0201_0603Metric",
            "0402": "Capacitor_SMD:C_0402_1005Metric",
            "0603": "Capacitor_SMD:C_0603_1608Metric",
            "0805": "Capacitor_SMD:C_0805_2012Metric",
            "1206": "Capacitor_SMD:C_1206_3216Metric",
            "1210": "Capacitor_SMD:C_1210_3225Metric",
            "1812": "Capacitor_SMD:C_1812_4532Metric",
            "2220": "Capacitor_SMD:C_2220_5750Metric",
        },
    ),
    "resistor": ComponentSpec(
        ref_des="R",
        derive_from="R",
        library_name="Resistor",
        source_library="Device.kicad_sym",
        footprints={
            "0201": "Resistor_SMD:R_0201_0603Metric",
            "0402": "Resistor_SMD:R_0402_1005Metric",
            "0603": "Resistor_SMD:R_0603_1608Metric",
            "0805": "Resistor_SMD:R_0805_2012Metric",
            "1206": "Resistor_SMD:R_1206_3216Metric",
            "1210": "Resistor_SMD:R_1210_3225Metric",
            "1812": "Resistor_SMD:R_1812_4532Metric",
            "2220": "Resistor_SMD:R_2220_5750Metric",
        },
    ),
    "inductor": ComponentSpec(
        ref_des="L",
        derive_from="L",
        library_name="Inductor",
        source_library="Device.kicad_sym",
        footprints={
            "0201": "Inductor_SMD:L_0201_0603Metric",
            "0402": "Inductor_SMD:L_0402_1005Metric",
            "0603": "Inductor_SMD:L_0603_1608Metric",
            "0805": "Inductor_SMD:L_0805_2012Metric",
            "1008": "Inductor_SMD:L_1008_2520Metric",
            "1206": "Inductor_SMD:L_1206_3216Metric",
            "1210": "Inductor_SMD:L_1210_3225Metric",
            "1812": "Inductor_SMD:L_1812_4532Metric",
            "2220": "Inductor_SMD:L_2220_5750Metric",
        },
    ),
}


class SymbolManager:
    def __init__(self, standard_library_path: Path, custom_library_base: Path, library_prefix: str, extra_symbol_paths: list[Path] | None = None):
        self.standard_library_path = standard_library_path
        self.custom_library_base = custom_library_base
        self.library_prefix = library_prefix
        self.extra_symbol_paths = extra_symbol_paths or []

    def resolve_footprint(self, spec: ComponentSpec, package: str) -> str:
        footprint = spec.footprints.get(package)
        if not footprint:
            known = ", ".join(spec.footprints)
            raise ValueError(f"Unknown package '{package}'. Known: {known}")
        return footprint

    def _apply_part_info(self, symbol, part: PartInfo, footprint: str) -> None:
        """Set properties and custom fields on a symbol from PartInfo."""
        prop_updates = {
            "Value": part.name,
            "Footprint": footprint,
            "Datasheet": part.datasheet,
            "Description": part.description,
        }
        for pname, pvalue in prop_updates.items():
            prop = symbol.get_property(pname)
            if prop:
                prop.value = pvalue

        custom_fields = {
            "Manufacturer": part.manufacturer,
            "Manufacturer Part Number": part.mpn,
            "Distributor Link 1": part.distributor_1_link,
            "Distributor 1 Part Number": part.distributor_1_part_number,
            "Distributor Link 2": part.distributor_2_link,
            "Distributor 2 Part Number": part.distributor_2_part_number,
        }
        for key, value in custom_fields.items():
            prop = Property(key, value)
            prop.effects.is_hidden = True
            symbol.properties.append(prop)

    def _write_to_library(self, symbol, custom_lib_path: Path) -> None:
        """Append symbol to custom library and write to disk."""
        if not custom_lib_path.is_file():
            empty_template = Path(__file__).resolve().parents[2] / "lib" / "kicad-library-utils" / "common" / "empty.kicad_sym"
            custom_lib_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(empty_template, custom_lib_path)
        custom_lib = KicadLibrary.from_file(str(custom_lib_path))
        custom_lib.symbols.append(symbol)
        custom_lib.write()

    def add_symbol(self, part: PartInfo, spec: ComponentSpec, footprint: str) -> str:
        """Add a specialized component symbol (capacitor/resistor/inductor)."""
        std_lib = KicadLibrary.from_file(str(self.standard_library_path / spec.source_library))
        base_symbol = next((s for s in std_lib.symbols if s.name == spec.derive_from), None)
        if not base_symbol:
            raise RuntimeError(f"Symbol '{spec.derive_from}' not found in '{spec.source_library}'")

        symbol = copy.deepcopy(base_symbol)
        symbol.name = f"{spec.ref_des}_{part.name}_{part.package}_{part.manufacturer}_{part.mpn}".replace(" ", "-")

        self._apply_part_info(symbol, part, footprint)

        custom_lib_path = self.custom_library_base / f"{self.library_prefix}{spec.library_name}.kicad_sym"
        self._write_to_library(symbol, custom_lib_path)

        return symbol.name

    def add_generic_symbol(
        self,
        part: PartInfo,
        source_library: str,
        derive_from: str,
        ref_des: str,
        footprint: str,
        target_library: str,
    ) -> str:
        """Add a generic symbol derived from any source library symbol."""
        std_lib = KicadLibrary.from_file(source_library)
        base_symbol = next((s for s in std_lib.symbols if s.name == derive_from), None)
        if not base_symbol:
            raise RuntimeError(f"Symbol '{derive_from}' not found in '{source_library}'")

        symbol = copy.deepcopy(base_symbol)
        symbol.name = f"{ref_des}_{part.name}_{part.package}_{part.manufacturer}_{part.mpn}".replace(" ", "-")

        self._apply_part_info(symbol, part, footprint)

        custom_lib_path = self.custom_library_base / target_library
        self._write_to_library(symbol, custom_lib_path)

        return symbol.name

    def get_symbol_properties(self, library_path: str, symbol_name: str) -> dict[str, str]:
        """Return {property_name: value} for all properties of a symbol."""
        lib = KicadLibrary.from_file(library_path)
        symbol = next((s for s in lib.symbols if s.name == symbol_name), None)
        if not symbol:
            return {}
        return {p.name: p.value for p in symbol.properties}

    def list_source_libraries(self) -> dict[str, Path]:
        """Return {display_name: absolute_path} for all source libraries."""
        result: dict[str, Path] = {}
        for p in sorted(self.standard_library_path.glob("*.kicad_sym")):
            result[p.name] = p.resolve()
        for extra_dir in self.extra_symbol_paths:
            extra = Path(extra_dir)
            if extra.is_dir():
                for p in sorted(extra.rglob("*.kicad_sym")):
                    display = str(p.relative_to(extra))
                    result[display] = p.resolve()
        return result

    def list_symbols_in_library(self, library_path: str) -> list[str]:
        lib = KicadLibrary.from_file(library_path)
        return [s.name for s in lib.symbols if s.extends is None]

    def list_custom_libraries(self) -> list[str]:
        pattern = f"{self.library_prefix}*.kicad_sym"
        return sorted(p.name for p in self.custom_library_base.glob(pattern))
