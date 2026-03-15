# CLAUDE.md

## What is this?

pklg is a CLI tool that generates KiCad symbol library entries by fetching part data from distributors (DigiKey) or manual entry, then deriving symbols from existing KiCad libraries. It follows personal naming/field conventions documented at https://meschter.me/posts/kicad-lib-conventions/.

## Quick reference

```bash
uv sync                  # install deps
uv run pklg add          # main command
uv run pytest tests/ -v  # run tests
```

Config lives at `~/.config/pklg.toml`.

## Architecture

- `cli.py` — Typer entry point, loads config, dispatches to flows
- `flows.py` — Interactive workflows: `add_specialized()` (cap/resistor/inductor) and `add_generic()` (any IC/symbol)
- `kicad.py` — `SymbolManager` handles symbol derivation, library I/O; `PartInfo`/`ComponentSpec` data models
- `editor.py` — Opens `$EDITOR` with TOML for reviewing/editing part info before committing
- `values.py` — SI prefix formatting (`4u7`, `10k`, `330n`) and parsing
- `distributors/` — `DigiKey` (API client with OAuth2), `Manual` (interactive prompts), `ProductResult` model
- `lib/kicad-library-utils/` — Git submodule; uses `kicad_sym.py` for reading/writing `.kicad_sym` files

## Conventions

- Symbol names: `<RefDes>_<Value>_<Package>_<Manufacturer>_<MPN>` — no spaces allowed (only `A-Z a-z 0-9 _ - . , +`)
- Library names: `MyLib_<Function>.kicad_sym` (prefix configurable)
- Python 3.14+, managed with uv
- Tests use pytest with JSON fixtures in `tests/fixtures/`
