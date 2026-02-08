# CLAUDE.md

## Project Overview

TPS Plots is a YAML-driven data visualization framework for The Planetary Society. Charts are defined in YAML and rendered to SVG, PNG, and PPTX with automatic desktop (16:10) and mobile (8:9) versions.

## Commands

```bash
uv sync --extra dev                    # Install dependencies

tpsplots generate yaml/chart.yaml      # Generate single chart
tpsplots generate yaml/                # Process all YAML in directory
tpsplots validate yaml/chart.yaml      # Validate without generating
tpsplots editor [yaml_dir]             # Launch interactive chart editor (default: yaml/)
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
| `tpsplots/models/charts/` | Per-chart-type config models (one file per chart type) |
| `tpsplots/models/mixins/` | Shared field groups (bar styling, base params, etc.) |
| `tpsplots/processors/` | Data transformations (see [PROCESSORS.md](PROCESSORS.md)) |
| `tpsplots/data_sources/` | Data loading (NASA budget, Google Sheets, etc.) |
| `tpsplots/editor/` | Interactive web editor (session, routes, static frontend) |
| `tpsplots/utils/` | Shared utilities (currency cleaning, DataFrame transforms, formatting) |

## Adding Chart Types

1. Create a config model in `tpsplots/models/charts/<type>.py` inheriting from `ChartConfigBase` (and relevant mixins)
2. Register the config in `CONFIG_REGISTRY` in `tpsplots/models/charts/__init__.py` and add to the `ChartConfig` union in `tpsplots/models/chart_config.py`
3. Create a view class in `tpsplots/views/` with `CONFIG_CLASS = <YourConfig>`
4. Register the view in `VIEW_REGISTRY` in `tpsplots/views/__init__.py`
5. Run `pytest tests/test_config_view_sync.py` to verify every `kwargs.pop()` in the view has a matching config field

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
  type: line | scatter | bar | donut | lollipop | stacked_bar | waffle | grouped_bar | us_map_pie | line_subplots  # line_subplots excluded from editor
  output: filename_stem
  title: "Chart Title"
  x: "{{column_name}}"      # Data reference syntax
  y: "{{other_column}}"
```

## Editor Frontend (JS)

Zero-build React 19 app using `htm` (tagged template literals, no JSX). CDN-loaded via ES module import maps — no TypeScript, no bundler, no transpilation.

**Shared modules — use these, don't duplicate:**

| Module | Provides | Import as |
|--------|----------|-----------|
| `static/js/lib/html.js` | `html` tagged template binding | `import { html } from "../lib/html.js"` |
| `static/js/components/fields/fieldComponents.js` | `FIELD_COMPONENTS` type→component map | `import { FIELD_COMPONENTS } from "./fieldComponents.js"` |
| `static/js/api.js` | All `fetch` wrappers | Named exports (`fetchSchema`, `fetchPreview`, etc.) |

**Key conventions:**
- Never `new Set()` / `new Map()` / `{}` inline in render — busts `useMemo` caches. Hoist to module-level constants or wrap in `useMemo`.
- Event handlers passed to hooks: use `useRef` to hold the latest handler (see `useHotkeys.js`) so the effect runs once.
- `window.dispatchEvent` bridges hotkeys (in App) to Header save/open actions — keep this pattern until save logic is lifted.

## Config/View Sync

Each view class has a `CONFIG_CLASS` pointing to its Pydantic config model. An AST-based test (`tests/test_config_view_sync.py`) enforces that every `kwargs.pop("key")` in view code has a matching field on the config model. If you add a new parameter to a view, add the field to its config model — the test will catch the drift.

## Semantic Colors

Use TPS brand names instead of hex codes: `Neptune Blue`, `Rocket Flame`, `Plasma Purple`, `Lunar Soil`. Full palette in `tpsplots/colors.py`.
