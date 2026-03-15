import tomllib
from pathlib import Path
from typing import Annotated

import questionary
import typer
from pydantic import BaseModel
from rich.console import Console

from .distributors import create_distributor
from .flows import add_generic, add_specialized, fetch_product
from .kicad import SymbolManager

console = Console()

app = typer.Typer()


class Config(BaseModel):
    stdlib_path: Path = Path("/usr/share/kicad/symbols/")
    library_path: Path
    library_prefix: str = "MyLib_"
    extra_symbol_paths: list[Path] = []
    raw_config: dict = {}


@app.command()
def add(ctx: typer.Context):
    cfg: Config = ctx.obj
    mgr = SymbolManager(
        cfg.stdlib_path, cfg.library_path, cfg.library_prefix, cfg.extra_symbol_paths
    )

    component_type = questionary.select(
        "Component type:",
        choices=["capacitor", "resistor", "inductor", "generic"],
        use_jk_keys=False,
    ).unsafe_ask()

    distributor_name = questionary.select(
        "Distributor:",
        choices=["digikey", "manual"],
        use_jk_keys=False,
    ).unsafe_ask()

    part_number = questionary.text("Distributor part number:").unsafe_ask()

    try:
        distributor = create_distributor(
            distributor_name, cfg.raw_config, component_type=component_type
        )
        product = fetch_product(distributor, part_number, console)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    console.print(f"  [bold]MPN:[/bold] {product.mpn}")
    console.print(f"  [bold]Manufacturer:[/bold] {product.manufacturer}")
    console.print(
        f"  [bold]Description:[/bold] {product.detailed_description or product.description}"
    )

    if not product.mpn:
        console.print(
            "[yellow]Warning: MPN is empty — the API response may have an unexpected format[/yellow]"
        )

    if component_type == "generic":
        add_generic(mgr, product, part_number, console)
    else:
        add_specialized(mgr, product, component_type, part_number, console)


DEFAULT_CONFIG = Path.home() / ".config" / "pklg.toml"


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[Path | None, typer.Option(dir_okay=False)] = DEFAULT_CONFIG,
):
    if not DEFAULT_CONFIG.exists():
        DEFAULT_CONFIG.touch()
    with DEFAULT_CONFIG.open("rb") as fd:
        loaded_config = tomllib.load(fd)
        if (
            "standard_symbol_library_path" in loaded_config
            and "stdlib_path" not in loaded_config
        ):
            loaded_config["stdlib_path"] = loaded_config.pop(
                "standard_symbol_library_path"
            )
        cfg = Config.model_validate({**loaded_config, "raw_config": loaded_config})
        ctx.obj = cfg


if __name__ == "__main__":
    app()
