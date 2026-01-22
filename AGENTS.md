# AGENTS.md

## Project Overview

TPS Plots (`tpsplots`) is a YAML-driven data visualization framework for The Planetary Society. It generates branded charts for web and presentations with automatic desktop (16:10) and mobile (8:9) versions and multiple outputs (SVG, PNG, PPTX, CSV).

## Architecture

Processing flow (v2.0 YAML spec):

```
YAML Config -> YAMLChartProcessor -> DataResolver -> View -> Output Files
                                 -> ParameterResolver
                                 -> MetadataResolver
```

Core directories:
- `tpsplots/models/` - Pydantic models for YAML validation
- `tpsplots/processors/` - YAML processing and data resolution
- `tpsplots/controllers/` - Chart generation logic and data preparation
- `tpsplots/data_sources/` - Data loading from Google Sheets, CSV, APIs
- `tpsplots/views/` - Chart rendering with matplotlib
- `tpsplots/utils/` - Shared utilities (date processing, formatting)
- `tpsplots/templates/` - YAML templates for chart generation

View registry and chart types:
- Registry: `tpsplots/views/__init__.py` (`VIEW_REGISTRY`)
- Type mapping: `tpsplots/models/chart_config.py` (`CHART_TYPES`)

## Setup

1. Use Python 3.10+ (3.11 recommended, matches GitHub Actions).

2. Sync dependencies (preferred):
   ```bash
   uv sync --extra dev
   ```

3. Alternative venv setup:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

4. Fonts are bundled in `tpsplots/assets/fonts/Poppins/` and auto-loaded.

## Common Commands

```bash
# Install dependencies and sync environment
uv sync --extra dev

# Generate charts from YAML
tpsplots yaml/chart.yaml           # Single file
tpsplots yaml/                     # All YAML files in directory

# Validate without generating
tpsplots --validate yaml/chart.yaml

# Custom output directory
tpsplots -o output/ yaml/chart.yaml

# Generate a new chart template
tpsplots --new line > my_chart.yaml

# List available chart types
tpsplots --list-types

# Generate JSON Schema for IDE autocomplete
tpsplots --schema > schema.json

# Run tests
pytest

# Lint and format
ruff check tpsplots/
ruff format tpsplots/
```

## Python API

```python
import tpsplots

# Generate charts
result = tpsplots.generate("yaml/chart.yaml")
result = tpsplots.generate("yaml/", outdir="output/")

# Check results
print(f"Succeeded: {result['succeeded']}, Failed: {result['failed']}")
```

## Outputs

- Generated charts go to `charts/` by default
- Outputs: `_desktop.svg`, `_mobile.svg`, `_desktop.png`, `_mobile.png`, `.pptx` (desktop only), `.csv` (when `export_data` is provided)
- These files are git-ignored; treat them as build artifacts
- CSV exports include metadata header rows; set `export_df.attrs["export_note"]` in controllers to add one or more "Note" rows

## YAML Structure

YAML configs use a two-level structure (v2.0 spec):

```yaml
data:     # Where data comes from
  source: data/file.csv | https://... | controller.method

chart:    # How to display it (type, metadata, parameters)
  type: line | bar | donut | lollipop | ...
  output: my_chart
  title: "Chart Title"
  ...
```

### Data Sources

Use a single `data.source` string. Optional prefixes (`csv:`, `url:`, `controller:`) are supported.

| Source | Description | Example |
|--------|-------------|---------|
| Local CSV | Relative CSV path | `data/source.csv` |
| URL CSV | Remote CSV URL | `https://.../export?format=csv` |
| Controller Method | Module + method | `nasa_budget_chart.method_name` |
| Custom Controller | Local file + method | `/path/to/controller.py:method_name` |

Controller resolution notes:
- For `module.method`, the processor loads the module from `tpsplots/controllers/`, finds the single `ChartController` subclass, and calls the method.

### Data References

Use `{{column_name}}` syntax to reference data columns:

```yaml
chart:
  x: "{{Year}}"              # Simple reference
  y: "{{data.values}}"       # Nested dot notation
  subtitle: "Total: {{sum}}" # Template substitution
```

Data references also support format specs: `{{value:.2f}}`.

## Key Files

| Location | Purpose |
|----------|---------|
| `tpsplots/__init__.py` | Public API, version, package init |
| `tpsplots/api.py` | `generate()` function |
| `tpsplots/cli.py` | Command-line interface |
| `tpsplots/exceptions.py` | Custom exception hierarchy |
| `tpsplots/models/` | Pydantic models for YAML validation |
| `tpsplots/processors/yaml_chart_processor.py` | Main YAML processing |
| `tpsplots/processors/resolvers/` | Data, parameter, metadata resolution |
| `tpsplots/processors/resolvers/reference_resolver.py` | `{{...}}` reference resolution |
| `tpsplots/templates/` | YAML templates for `--new` command |
| `tpsplots/views/` | Chart view classes |
| `tpsplots/views/style/tps_base.mplstyle` | TPS matplotlib styling |
| `yaml/` | YAML chart configurations |
| `tests/` | Test suite |

## Adding New Charts

### Option 1: YAML Only (Recommended)

Generate a template and customize:

```bash
tpsplots --new line > yaml/my_new_chart.yaml
```

Or create manually in `yaml/`:

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv

chart:
  type: line
  output: my_new_chart
  title: "Chart Title"
  source: "Data Source"

  x: "{{Year}}"
  y: "{{Value}}"
  color: Neptune Blue
```

### Option 2: Custom Controller

For complex data processing, create a controller in `tpsplots/controllers/`:

```python
from tpsplots.controllers.chart_controller import ChartController

class MyController(ChartController):
    def my_data_method(self):
        # Process data and return dict
        return {"x": [...], "y": [...], "export_df": df}
```

Reference in YAML:
```yaml
data:
  source: my_controller.my_data_method
```

## Chart Types

| Type | Description |
|------|-------------|
| `line` | Multi-series line charts |
| `bar` | Vertical or horizontal bar charts |
| `donut` | Donut/pie charts |
| `lollipop` | Timeline/range visualization |
| `stacked_bar` | Stacked bar charts |
| `waffle` | Waffle/grid charts |
| `us_map_pie` | US map with pie overlays |
| `line_subplots` | Multiple subplot panels |
| `grouped_bar` | Grouped/clustered bars |

## Semantic Colors

Use TPS brand color names (from `tpsplots/colors.py`) instead of hex codes:

| Name | Hex | Usage |
|------|-----|-------|
| `Neptune Blue` | `#037CC2` | Primary |
| `Rocket Flame` | `#FF5D47` | Accent |
| `Plasma Purple` | `#643788` | Secondary |
| `Lunar Soil` | `#8C8C8C` | Gray |
| `Crater Shadow` | `#414141` | Dark |

## Deploy (S3)

```bash
python scripts/s3_sync.py --local-dir charts --bucket planetary --prefix assets/charts/
```

Use `--dry-run` to preview. Requires AWS credentials.

## Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tpsplots

# Run specific test file
pytest tests/test_api.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TPSPLOTS_HEADLESS` | Force headless mode (`1`) or GUI mode (`0`) |
