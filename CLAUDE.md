# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TPS Plots is a YAML-driven data visualization framework for The Planetary Society that generates branded charts for web and presentations. Charts are defined declaratively in YAML files and processed into multiple output formats (SVG, PNG, PPTX) with automatic desktop (16:10) and mobile (8:9) responsive versions.

## Common Commands

```bash
# Install dependencies and sync environment
uv sync --extra dev

# Generate charts from YAML
tpsplots yaml/chart_name.yaml          # Single file
tpsplots yaml/                         # Process all YAML files in directory

# Validate YAML without generating
tpsplots --validate yaml/chart_name.yaml

# Run tests
pytest                                 # All tests
pytest tests/test_api.py              # Single test file
pytest tests/test_api.py::test_name   # Single test

# Linting and formatting
ruff check tpsplots/                  # Check for issues
ruff format tpsplots/                 # Format code
```

## Architecture

### MVC Pattern with YAML Configuration

The codebase follows an MVC pattern where YAML files are the primary interface:

```
YAML Config → YAMLChartProcessor → DataResolver → View → Output Files
                                 → ParameterResolver
                                 → MetadataResolver
```

**Key processing flow** (`tpsplots/processors/yaml_chart_processor.py`):
1. Load and validate YAML against Pydantic models
2. Resolve data source (CSV, URL, or controller method)
3. Resolve `{{variable}}` references in parameters and metadata
4. Dispatch to appropriate view class for rendering

### Core Components

| Directory | Purpose |
|-----------|---------|
| `tpsplots/views/` | Chart rendering classes (one per chart type), inherit from `ChartView` |
| `tpsplots/controllers/` | Data preparation logic, inherit from `ChartController` |
| `tpsplots/models/` | Pydantic validation schemas for YAML configs |
| `tpsplots/processors/resolvers/` | Handle `{{variable}}` substitution from data |
| `tpsplots/data_sources/` | Data loading (NASA budget, Google Sheets, etc.) |

### View Registry

Chart types are registered in `tpsplots/views/__init__.py` via `VIEW_REGISTRY`. The mapping follows the pattern `type_name_plot` → `ViewClass`. When adding new chart types:
1. Create view class in `tpsplots/views/`
2. Add to `VIEW_REGISTRY` in `tpsplots/views/__init__.py`
3. Add type mapping in `tpsplots/models/chart_config.py` `CHART_TYPES`

### YAML v2.0 Spec

Charts use a two-section structure (see `YAML_SPEC.md` for full details):

```yaml
data:
  source: data/file.csv | https://url | controller.method

chart:
  type: line | bar | donut | lollipop | stacked_bar | waffle
  output: filename_stem
  title: "Chart Title"
  x: "{{column_name}}"      # Data reference syntax
  y: "{{other_column}}"
```

Data references use `{{column_name}}` syntax with support for:
- Dot notation: `{{data.nested.value}}`
- Format specs: `{{value:.2f}}`

### Controller Methods as Data Sources

When `data.source` is `module.method`, the processor:
1. Looks in `tpsplots/controllers/` for the module
2. Finds the single `ChartController` subclass
3. Calls the method, which must return a dict

### Processors

Data transformation processors live in `tpsplots/processors/`. See **[PROCESSORS.md](PROCESSORS.md)** for detailed guidelines on creating new processors.

Key principles:
- Single responsibility (one transformation per processor)
- No presentation logic (colors, scaling, formatting belong in views)
- Always return DataFrame for pipeline chaining
- Must have unit tests

### Semantic Colors

Use TPS brand color names (space-separated) instead of hex codes:
- `Neptune Blue` (#037CC2) - Primary
- `Rocket Flame` (#FF5D47) - Accent
- `Plasma Purple` (#643788) - Secondary
- `Lunar Soil` (#8C8C8C) - Gray

Full palette in `tpsplots/colors.py` (`TPS_COLORS` dict).

## Output Structure

Each chart generates:
- `{output}_desktop.svg/png` - Desktop version (16:10)
- `{output}_mobile.svg/png` - Mobile version (8:9)
- `{output}.pptx` - PowerPoint (desktop only)
- `{output}.csv` - Data export (if `export_data` specified)
