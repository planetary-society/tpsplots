# CLAUDE.md

## Project Overview

TPS Plots is a YAML-driven data visualization framework for The Planetary Society. Charts are defined in YAML and rendered to SVG, PNG, and PPTX with automatic desktop (16:10) and mobile (8:9) versions.

## Commands

```bash
uv sync --extra dev                    # Install dependencies

tpsplots generate yaml/chart.yaml      # Generate single chart
tpsplots generate yaml/                # Process all YAML in directory
tpsplots validate yaml/chart.yaml      # Validate without generating
tpsplots s3-sync --bucket X --prefix Y --local-dir charts/  # Sync to S3

pytest                                 # Run tests
ruff check tpsplots/ && ruff format tpsplots/  # Lint and format
```

## Architecture

MVC pattern with YAML as the primary interface:

```
YAML Config → YAMLChartProcessor → DataResolver → View → Output Files
```

| Directory | Purpose |
|-----------|---------|
| `tpsplots/views/` | Chart rendering (inherit from `ChartView`) |
| `tpsplots/controllers/` | Data preparation (inherit from `ChartController`) |
| `tpsplots/models/` | Pydantic schemas for YAML validation |
| `tpsplots/processors/` | Data transformations (see [PROCESSORS.md](PROCESSORS.md)) |
| `tpsplots/data_sources/` | Data loading (NASA budget, Google Sheets, etc.) |
| `tpsplots/utils/` | Shared utilities (currency cleaning, DataFrame transforms, formatting) |

## Adding Chart Types

1. Create view class in `tpsplots/views/`
2. Register in `VIEW_REGISTRY` in `tpsplots/views/__init__.py`
3. Add type to `CHART_TYPES` in `tpsplots/models/chart_config.py`

## YAML Structure

Schema defined in `tpsplots/models/yaml_config.py`. Run `tpsplots --schema` for full JSON schema.

```yaml
data:
  source: data/file.csv | https://url | controller.method
  params:                         # Optional: customize data loading
    columns: [col1, col2]         # Keep only these columns
    cast: {Year: int}             # Type conversion (int, float, str, datetime)
    renames: {Old: New}           # Rename columns
    auto_clean_currency: true     # Clean $X,XXX columns (default for URLs)
  calculate_inflation:            # Optional: inflation adjustment
    columns: [Amount]             # Columns to adjust
    type: nnsi                    # nnsi (default) or gdp

chart:
  type: line | bar | donut | lollipop | stacked_bar | waffle
  output: filename_stem
  title: "Chart Title"
  x: "{{column_name}}"      # Data reference syntax
  y: "{{other_column}}"
```

## Semantic Colors

Use TPS brand names instead of hex codes: `Neptune Blue`, `Rocket Flame`, `Plasma Purple`, `Lunar Soil`. Full palette in `tpsplots/colors.py`.
