"""Workflow orchestration for adding components."""

import questionary
import typer
from rich.console import Console

from .distributors import Distributor, ProductResult
from .editor import edit_part_info
from .kicad import COMPONENT_SPECS, PartInfo, SymbolManager
from .values import format_short_value


def fetch_product(
    distributor: Distributor,
    part_number: str,
    console: Console,
) -> ProductResult:
    """Fetch a product from the distributor (API or manual entry)."""
    if distributor.interactive:
        return distributor.query(part_number)
    with console.status("Fetching product details..."):
        return distributor.query(part_number)


def add_specialized(
    mgr: SymbolManager,
    product: ProductResult,
    component_type: str,
    distributor_pn: str,
    console: Console,
) -> None:
    """Add a specialized component (capacitor/resistor/inductor)."""
    spec = COMPONENT_SPECS[component_type]

    # Detect and warn on category mismatch
    if product.component_type and product.component_type != component_type:
        console.print(
            f"[yellow]Warning: distributor categorizes this as '{product.component_type}', "
            f"you selected '{component_type}'[/yellow]"
        )

    # Package
    package = product.package
    if not package:
        console.print("[yellow]Could not auto-detect package[/yellow]")
        package = questionary.text(
            "Enter imperial package code (e.g. 0805):"
        ).unsafe_ask()

    # Footprint
    try:
        footprint = mgr.resolve_footprint(spec, package)
    except ValueError:
        console.print(f"[yellow]No known footprint for package '{package}'[/yellow]")
        footprint = questionary.text("Enter full footprint path:").unsafe_ask()

    # Value / name
    auto_name = ""
    if product.value_number is not None and product.value_prefix is not None:
        try:
            auto_name = format_short_value(product.value_number, product.value_prefix, component_type)
        except ValueError:
            pass

    name = questionary.text(
        "Value (e.g. 330n, 10k, 4u7):", default=auto_name
    ).unsafe_ask()

    part = PartInfo(
        name=name,
        package=package,
        manufacturer=product.manufacturer,
        mpn=product.mpn,
        datasheet=product.datasheet_url,
        description=product.detailed_description or product.description,
        distributor_1_link=product.product_url,
        distributor_1_part_number=distributor_pn,
    )

    symbol_name = f"{spec.ref_des}_{name}_{package}_{product.manufacturer}_{product.mpn}"
    target_library = f"{mgr.library_prefix}{spec.library_name}.kicad_sym"

    result = edit_part_info(part, footprint, symbol_name, target_library)
    if result is None:
        console.print("Aborted.")
        raise typer.Exit()

    part, footprint = result

    if not questionary.confirm("Add this symbol?", default=True).unsafe_ask():
        console.print("Cancelled.")
        raise typer.Exit()

    symbol_name = mgr.add_symbol(part, spec, footprint)
    console.print(f"[green]Added symbol '[bold]{symbol_name}[/bold]' to {target_library}[/green]")


def add_generic(
    mgr: SymbolManager,
    product: ProductResult,
    distributor_pn: str,
    console: Console,
) -> None:
    """Add a generic component derived from a source library symbol."""
    # Browse source libraries (standard + extra)
    source_libs = mgr.list_source_libraries()
    choices = [questionary.Choice(title=name, value=str(path)) for name, path in source_libs.items()]
    source_library = questionary.select(
        "Pick a source library:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
    ).unsafe_ask()

    # Pick symbol from that library
    symbols = mgr.list_symbols_in_library(source_library)
    derive_from = questionary.select(
        "Pick a symbol to derive from:",
        choices=symbols,
        use_search_filter=True,
        use_jk_keys=False,
    ).unsafe_ask()

    # Pick target custom library or create new
    custom_libs = mgr.list_custom_libraries()
    choices = custom_libs + ["-- Create new --"]
    target_choice = questionary.select(
        "Target library:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
    ).unsafe_ask()

    if target_choice == "-- Create new --":
        lib_name = questionary.text("New library name (without prefix/extension):").unsafe_ask()
        target_library = f"{mgr.library_prefix}{lib_name}.kicad_sym"
    else:
        target_library = target_choice

    # Read properties from the source symbol to use as defaults
    src_props = mgr.get_symbol_properties(source_library, derive_from)

    # Reference designator — use from symbol if available
    src_ref = src_props.get("Reference", "")
    if src_ref:
        ref_des = src_ref
        console.print(f"  [dim]Reference designator:[/dim] {ref_des}")
    else:
        ref_des = questionary.text("Reference designator (e.g. U, J, D):").unsafe_ask()

    # Footprint — use from symbol if available
    src_footprint = src_props.get("Footprint", "")
    if src_footprint:
        footprint = src_footprint
        console.print(f"  [dim]Footprint:[/dim] {footprint}")
    else:
        footprint = questionary.text("Footprint (e.g. Package_SO:SOIC-8_3.9x4.9mm_P1.27mm):").unsafe_ask()

    # Component name — default to the source symbol name
    name = questionary.text("Component name (identifier for symbol):", default=derive_from).unsafe_ask()

    # Package
    package = product.package or ""
    if not package:
        package = questionary.text("Package code (e.g. SOIC-8):").unsafe_ask()

    # Prefer source symbol's datasheet/description over distributor's if available
    datasheet = src_props.get("Datasheet", "") or product.datasheet_url
    description = src_props.get("Description", "") or product.detailed_description or product.description

    part = PartInfo(
        name=name,
        package=package,
        manufacturer=product.manufacturer,
        mpn=product.mpn,
        datasheet=datasheet,
        description=description,
        distributor_1_link=product.product_url,
        distributor_1_part_number=distributor_pn,
    )

    symbol_name = f"{ref_des}_{name}_{package}_{product.manufacturer}_{product.mpn}".replace(" ", "-")

    result = edit_part_info(part, footprint, symbol_name, target_library)
    if result is None:
        console.print("Aborted.")
        raise typer.Exit()

    part, footprint = result

    if not questionary.confirm("Add this symbol?", default=True).unsafe_ask():
        console.print("Cancelled.")
        raise typer.Exit()

    symbol_name = mgr.add_generic_symbol(
        part,
        source_library=source_library,
        derive_from=derive_from,
        ref_des=ref_des,
        footprint=footprint,
        target_library=target_library,
    )
    console.print(f"[green]Added symbol '[bold]{symbol_name}[/bold]' to {target_library}[/green]")
