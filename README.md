# pklg

A CLI tool for generating KiCad symbol library entries. Fetches part data from distributors (DigiKey) or manual entry, derives symbols from existing KiCad libraries, and writes them to your custom libraries following consistent naming and field conventions.

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone --recurse-submodules <repo-url>
cd pklg
uv sync
```

## Usage

```bash
pklg add
```

The interactive flow prompts you through:

1. **Component type** -- capacitor, resistor, inductor, or generic
2. **Distributor** -- DigiKey (API) or manual entry
3. **Distributor part number** -- used to fetch product details
4. **Component-specific prompts** -- depends on the type selected (see below)
5. **Editor review** -- opens `$EDITOR` with a TOML file to review/edit all fields before committing
6. **Confirmation** -- final yes/no before writing the symbol

### Specialized components (capacitor, resistor, inductor)

For passive components, pklg auto-detects package code and electrical value from the distributor data and maps them to standard SMD footprints (0201 through 2220). Values are formatted in EE shorthand (`4u7`, `10k`, `330n`).

The symbol is derived from the generic `C`, `R`, or `L` symbol in KiCad's `Device.kicad_sym` library and written to `MyLib_Capacitor.kicad_sym`, `MyLib_Resistor.kicad_sym`, or `MyLib_Inductor.kicad_sym` respectively.

### Generic components (ICs, connectors, etc.)

For anything else, pklg lets you browse and pick a source symbol from any KiCad symbol library -- both the standard KiCad libraries and any 3rdparty libraries you configure.

Properties already present on the source symbol (reference designator, footprint, datasheet, description) are automatically carried over. You only need to provide a component name and package code.

The flow:

1. Pick a source library (searchable, includes standard + 3rdparty)
2. Pick a symbol to derive from
3. Pick or create a target custom library
4. Enter component name (defaults to source symbol name)
5. Enter package code
6. Review in editor, confirm

## Configuration

Config file: `~/.config/pklg.toml` (created automatically on first run).

```toml
# Required: where to write your custom symbol libraries
library_path = "/home/user/kicad-libs/Symbols"

# Optional: path to KiCad's standard symbol libraries (default shown)
standard_symbol_library_path = "/usr/share/kicad/symbols/"

# Optional: custom library filename prefix (default: "MyLib_")
library_prefix = "MyLib_"

# Optional: additional directories to scan for .kicad_sym files (recursive)
# Useful for KiCad 3rdparty plugin libraries
extra_symbol_paths = ["/home/user/.local/share/kicad/9.0/3rdparty/symbols"]

# Required for DigiKey distributor
[digikey]
client_id = "your-client-id"
client_secret = "your-client-secret"
```

### Config options

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `library_path` | Yes | -- | Directory where custom `.kicad_sym` files are written |
| `standard_symbol_library_path` | No | `/usr/share/kicad/symbols/` | KiCad standard symbol library path |
| `library_prefix` | No | `MyLib_` | Prefix for custom library filenames |
| `extra_symbol_paths` | No | `[]` | Additional directories to scan recursively for source `.kicad_sym` files |
| `digikey.client_id` | For DigiKey | -- | DigiKey API client ID |
| `digikey.client_secret` | For DigiKey | -- | DigiKey API client secret |

### DigiKey API setup

Register an application at [DigiKey API](https://developer.digikey.com/) to get a client ID and secret. pklg uses the client credentials OAuth2 flow (no browser login required).

## Naming conventions

pklg follows the naming convention documented at https://meschter.me/posts/kicad-lib-conventions/.

**Symbol names:** `<RefDes>_<Value>_<Package>_<Manufacturer>_<MPN>`

- Only characters `A-Z a-z 0-9 _ - . , +` are allowed (spaces are replaced with hyphens)
- Examples:
  - `C_100nF_0402_Murata_GRM155R71C104KA88`
  - `U_nRF54L15-QFXX_QFN-48_Nordic-Semiconductor-ASA_NRF54L15-QFAA-R`

**Library names:** `MyLib_<Function>.kicad_sym`

- Examples: `MyLib_Capacitor.kicad_sym`, `MyLib_MCU.kicad_sym`, `MyLib_Connector.kicad_sym`

**Fields written to each symbol:**

| Field | Source |
|-------|--------|
| Value | Component name / EE shorthand value |
| Footprint | Auto-detected or from source symbol |
| Datasheet | From distributor or source symbol |
| Description | From distributor or source symbol |
| Manufacturer | From distributor |
| Manufacturer Part Number | From distributor |
| Distributor Link 1 | Product URL from distributor |
| Distributor 1 Part Number | The part number you entered |
| Distributor Link 2 | Optional, set in editor |
| Distributor 2 Part Number | Optional, set in editor |

## Editor review

Before writing any symbol, pklg opens your `$EDITOR` (defaults to `vi`) with a TOML file containing all fields. You can edit any value, including the symbol name and target library. Delete all content to abort.

## Development

```bash
uv sync                     # install dependencies
uv run pytest tests/ -v     # run tests
uv run ruff check           # lint
```
