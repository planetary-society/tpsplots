# TPS Plots

A data visualization framework for The Planetary Society that creates consistent, branded charts for web and presentations.

## Features

- **YAML-Driven Chart Generation** - Define charts declaratively without writing Python code
- **Multiple Chart Types** - Line, bar, lollipop, donut, waffle, stacked bar, and more
- **Automatic Responsive Output** - Generates both desktop (16:10) and mobile (8:9) versions
- **Multi-Format Export** - SVG, PNG, PPTX, and CSV data export
- **Flexible Data Sources** - Google Sheets, CSV files, or custom controller methods
- **TPS Brand Styling** - Consistent Planetary Society branding with Poppins fonts

## Quick Start

### 1. Create a YAML Configuration

```yaml
# my_chart.yaml
data:
  source: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv

chart:
  type: line
  output: my_first_chart
  title: "My Chart Title"
  subtitle: "A descriptive subtitle for context"
  source: "Data Source Attribution"

  x: "{{Year}}"
  y: ["{{Value1}}", "{{Value2}}"]
  color: [NeptuneBlue, RocketFlame]
  label: ["Series A", "Series B"]
```

### 2. Generate the Chart

**CLI:**
```bash
tpsplots generate my_chart.yaml
```

**Python:**
```python
import tpsplots

result = tpsplots.generate("my_chart.yaml")
print(f"Generated {result['succeeded']} charts")
```

### 3. Find Your Output

Charts are saved to `charts/` by default:
- `my_first_chart_desktop.svg` / `my_first_chart_mobile.svg`
- `my_first_chart_desktop.png` / `my_first_chart_mobile.png`
- `my_first_chart.pptx` (desktop only)
- `my_first_chart.csv` (if `export_data` specified)

---

## YAML Structure

TPS Plots uses a clean two-level YAML structure:

```yaml
data:     # Where data comes from
  source: data/file.csv | https://... | controller.method

chart:    # How to display it
  type: line | bar | donut | ...
  output: chart_name
  title: "Chart Title"
  ...     # Chart-specific parameters
```

### Data References

Use `{{column_name}}` syntax to reference data columns:

```yaml
chart:
  x: "{{Year}}"                    # Simple column reference
  y: "{{data.series.values}}"      # Nested dot notation
  subtitle: "Total: {{sum:.2f}}"   # Format string (2 decimal places)
```

---

## Real-World Examples

### Example 1: Line Chart with Historical Data

Track NASA budget over time with projections:

```yaml
# nasa_budget_by_year_with_projection.yaml
data:
  source: nasa_budget_chart.nasa_budget_by_year_with_projection_inflation_adjusted

chart:
  type: line
  output: nasa_budget_by_year_with_projection_inflation_adjusted
  title: How NASA's budget has changed over time
  subtitle: After its peak during Apollo, NASA's inflation-adjusted budget has held
    relatively steady, though that may change.
  source: NASA Budget Requests

  x: "{{fiscal_years}}"
  y:
    - "{{appropriation_adjusted_nnsi}}"
    - "{{white_house_budget_projection}}"
  color: [NeptuneBlue, RocketFlame]
  linestyle: ["-", "-"]
  marker: ["", "o"]
  label: ["", "Proposed"]
  xlim: "{{xlim}}"
  ylim: "{{ylim}}"
  scale: billions
  legend: "{{legend}}"
  export_data: "{{export_df}}"
```

### Example 2: Horizontal Bar Chart from Google Sheets

Compare spacecraft development timelines with data from a Google Sheet:

```yaml
# human_spacecraft_dev_times.yaml
data:
  source: https://docs.google.com/spreadsheets/d/1uYSirJmE0gLQ701iBFZASsTQL0od36l9xJ7jbEagnrY/export?format=csv

chart:
  type: bar
  output: human_spaceflight_development_comparisons
  title: "A five year sprint to the Moon?"
  subtitle: "A new entrant to provide crewed landings for NASA's Artemis program
    by 2030 has five years to design and build their spacecraft."
  source: "Official Reporting. Details: planet.ly/hsfdevtimes"

  categories: "{{Spacecraft}}"
  values: "{{Duration (years)}}"
  orientation: horizontal
  xlabel: "Years from prime contract award to first crewed flight"
  sort_by: value
  sort_ascending: false
  height: 0.5
  grid: true
  xlim: [0, 20]
  show_values: true
  value_format: ".1f"
  value_suffix: " yrs"
  value_fontsize: 10
  label_size: 14
  tick_size: 16
  colors:
    - LunarSoil     # Mercury
    - LunarSoil     # Gemini
    - LunarSoil     # Apollo CSM
    - LunarSoil     # Apollo LM
    - LunarSoil     # Shuttle Orbiter
    - LunarSoil     # Orion
    - LunarSoil     # Crew Dragon
    - LunarSoil     # Starliner
    - LunarSoil     # Starship HLS
    - LunarSoil     # Blue Moon
    - RocketFlame   # New HLS Entrant (highlighted)
```

### Example 3: Lollipop Chart with Timeline Ranges

Visualize development periods with start and end dates:

```yaml
# human_spaceflight_development_times.yaml
data:
  source: https://docs.google.com/spreadsheets/d/1uYSirJmE0gLQ701iBFZASsTQL0od36l9xJ7jbEagnrY/export?format=csv

chart:
  type: lollipop
  output: human_spaceflight_development_comparisons
  title: "Human Spaceflight Development Times Comparison"
  subtitle: "To make a 2030 landing deadline, a new human landing spacecraft would
    need be the fastest program development in 65 years."
  source: "NASA Historical Data"

  categories: "{{Spacecraft}}"
  start_values: "{{Start Date_year}}"
  end_values: "{{First Crewed Utilization_year}}"
  xlim: [1959, 2031]
  y_axis_position: right
  hide_y_spine: true

  # Color by era: blue for historical, purple for future
  colors:
    - NeptuneBlue   # Mercury through Starliner (historical)
    - NeptuneBlue
    - NeptuneBlue
    - NeptuneBlue
    - NeptuneBlue
    - NeptuneBlue
    - NeptuneBlue
    - NeptuneBlue
    - PlasmaPurple  # Future HLS projects
    - PlasmaPurple
    - PlasmaPurple

  # Solid for completed, dotted for projected
  linestyle: ["-", "-", "-", "-", "-", "-", "-", "-", ":", ":", ":"]

  marker_size: 5
  line_width: 5
  grid: true
  grid_axis: x
  range_labels: true
  range_suffix: " yrs"
  export_data: "{{data}}"
```

### Example 4: Donut Chart for Budget Breakdown

Show NASA budget allocation by directorate:

```yaml
# nasa_major_activities_donut.yaml
data:
  source: nasa_budget_chart.nasa_major_activites_donut_chart

chart:
  type: donut
  output: nasa_directorate_breakdown_donut_chart
  title: NASA's budget is subdivided by mission area
  subtitle: "Directorates are responsible for distinct activities — from science
    to facilities — and they don't share funding."
  source: NASA FY2025 Budget Request

  values: "{{sorted_values}}"
  labels: "{{sorted_labels}}"
  show_percentages: true
  label_distance: 1.1
  hole_size: 0.6
  center_text: NASA
  center_color: white
  export_data: "{{export_df}}"
```

### Example 5: Multi-Series Comparison with Direct Labels

Compare contract awards across fiscal years:

```yaml
# fy2025_new_contracts_comparison.yaml
data:
  source: fy2025_charts.new_contract_awards_comparison_to_prior_years

chart:
  type: line
  output: new_contracts_historical_comparison
  title: "NASA's total new contract awards in FY 2025"
  subtitle: "While below the recent average, the total number was similar to that in 2024."
  source: "USASpending.gov (Does not include IDVs)"

  x: "{{months}}"
  y: "{{y_series}}"
  color: "{{colors}}"
  linestyle: "{{linestyles}}"
  linewidth: "{{linewidths}}"
  marker: "{{markers}}"
  label: "{{labels}}"
  ylim: [0, 6000]
  ylabel: "Cumulative New Contracts Awarded"
  label_size: 13
  tick_size: 14
  grid: true
  legend: false
  direct_line_labels:
    fontsize: 10
  export_data: "{{export_df}}"
```

---

## Chart Types Reference

| Type | Description | Key Parameters |
|------|-------------|----------------|
| `line` | Multi-series line charts | `x`, `y`, `color`, `linestyle`, `marker`, `label` |
| `bar` | Vertical or horizontal bars | `categories`, `values`, `orientation`, `colors` |
| `lollipop` | Timeline/range visualization | `categories`, `start_values`, `end_values`, `colors` |
| `donut` | Donut/pie charts | `values`, `labels`, `hole_size`, `center_text` |
| `stacked_bar` | Stacked bar charts | `categories`, `values`, `colors` |
| `waffle` | Waffle/grid charts | `values`, `labels`, `rows`, `columns` |
| `us_map_pie` | US map with pie overlays | `state_data`, `pie_values` |
| `line_subplots` | Multiple subplot panels | `subplot_data`, `grid_shape` |

List all available types: `tpsplots --list-types`

---

## Data Sources

Use a single `data.source` string. Optional prefixes (`csv:`, `url:`, `controller:`) can make intent explicit.

### URL (Google Sheets, Remote CSV)

Fetch data directly from any URL that returns CSV:

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv
```

**Tips:**
- Sheet must be publicly accessible or "Anyone with link can view"
- Use the `/export?format=csv` URL format
- For specific sheets/tabs, add `&gid=SHEET_GID`

### CSV Files (Local Data)

Load from a local CSV file:

```yaml
data:
  source: data/my_data.csv
```

### Controller Methods (Complex Data Processing)

Use existing Python controllers for advanced data manipulation:

```yaml
data:
  source: nasa_budget_chart.nasa_budget_by_year_inflation_adjusted
```

Controller modules must contain exactly one `ChartController` subclass with the method, and the method must return a dict.

If the controller lives outside your Python path, provide a local file path:

```yaml
data:
  source: /path/to/custom_controller.py:my_data_method
```

**Available Controllers (module names):**
- `nasa_budget_chart` - NASA budget analysis
- `fy2025_charts` / `fy2026_charts`
- `china_comparisons_controller`
- `mission_spending_controller`

---

## Semantic Colors

Use TPS brand color names instead of hex codes:

| Name | Hex | Usage |
|------|-----|-------|
| `NeptuneBlue` | `#037CC2` | Primary |
| `RocketFlame` | `#FF5D47` | Accent |
| `PlasmaPurple` | `#643788` | Secondary |
| `LunarSoil` | `#8C8C8C` | Gray |
| `CraterShadow` | `#414141` | Dark |

---

## CLI Reference

The CLI uses subcommands for different operations:

```bash
tpsplots [OPTIONS] COMMAND [ARGS]...
```

### Global Options

```
--version       Show version and exit
--schema        Print JSON Schema for YAML configuration and exit
--list-types    List available chart types and exit
--new TYPE      Generate a YAML template for the specified chart type
--help          Show help message
```

### Commands

#### `generate` - Generate Charts

```bash
tpsplots generate [OPTIONS] INPUTS...
```

| Option | Description |
|--------|-------------|
| `-o, --outdir PATH` | Output directory (default: `charts/`) |
| `--strict` | Error on unresolved data references |
| `-q, --quiet` | Suppress progress output |
| `--verbose` | Enable verbose/debug logging |

#### `validate` - Validate Configuration

```bash
tpsplots validate [OPTIONS] INPUTS...
```

| Option | Description |
|--------|-------------|
| `--strict` | Error on unresolved data references |
| `-q, --quiet` | Suppress progress output |
| `--verbose` | Enable verbose/debug logging |

#### `s3-sync` - Upload to S3

```bash
tpsplots s3-sync [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-d, --local-dir PATH` | Local directory to upload (required) |
| `-b, --bucket TEXT` | S3 bucket name (required) |
| `-p, --prefix TEXT` | S3 prefix/path within bucket (required) |
| `-n, --dry-run` | Preview changes without uploading |

### Examples

```bash
# Generate single chart
tpsplots generate yaml/my_chart.yaml

# Process entire directory
tpsplots generate yaml/

# Validate without generating
tpsplots validate yaml/my_chart.yaml

# Custom output directory
tpsplots generate -o output/ yaml/

# Generate JSON Schema for IDE support
tpsplots --schema > tpsplots-schema.json

# Generate a new chart template
tpsplots --new line > yaml/my_new_chart.yaml

# Upload charts to S3 (dry-run first)
tpsplots s3-sync -d charts -b mybucket -p assets/charts/ --dry-run
```

---

## Python API

```python
import tpsplots

# Generate from single file
result = tpsplots.generate("chart.yaml")

# Generate from directory
result = tpsplots.generate("yaml/", outdir="output/")

# With options
result = tpsplots.generate(
    "chart.yaml",
    outdir="custom_output/",
    strict=True,   # Error on unresolved references
    quiet=True     # Suppress logging
)

# Check results
print(f"Succeeded: {result['succeeded']}")
print(f"Failed: {result['failed']}")
print(f"Files: {result['files']}")
print(f"Errors: {result['errors']}")
```

### Exception Handling

```python
import tpsplots
from tpsplots import ConfigurationError, DataSourceError, RenderingError

try:
    result = tpsplots.generate("chart.yaml")
except ConfigurationError as e:
    print(f"Invalid YAML configuration: {e}")
except DataSourceError as e:
    print(f"Could not load data: {e}")
except RenderingError as e:
    print(f"Chart rendering failed: {e}")
```

---

## Project Structure

```
tpsplots/
├── __init__.py              # Public API and package initialization
├── api.py                   # generate() function implementation
├── cli.py                   # Command-line interface
├── exceptions.py            # TPSPlotsError, ConfigurationError, etc.
├── schema.py                # JSON Schema generation
├── assets/                  # Bundled resources
│   ├── fonts/Poppins/       # TPS brand fonts
│   └── images/              # TPS logo
├── controllers/             # Chart generation logic
│   ├── nasa_budget_chart.py
│   ├── fy2025_charts.py
│   └── ...
├── data_sources/            # Data loading and processing
│   ├── google_sheets_source.py
│   ├── nasa_budget_data_source.py
│   └── ...
├── models/                  # Pydantic validation models
│   ├── chart_config.py
│   ├── data_sources.py
│   ├── parameters.py
│   └── yaml_config.py
├── processors/              # YAML processing pipeline
│   ├── yaml_chart_processor.py
│   └── resolvers/           # Data, parameter, metadata resolution
├── templates/               # Chart type templates for --new
├── utils/                   # Shared utilities
│   ├── date_processing.py
│   └── formatting.py
└── views/                   # Chart visualization classes
    ├── chart_view.py        # Base class
    ├── line_chart.py
    ├── bar_chart.py
    ├── lollipop_chart.py
    ├── donut_chart.py
    └── style/               # Matplotlib style files
```

---

## Advanced Usage

### Creating Custom Controllers

For complex data processing, create a custom controller:

```python
# tpsplots/controllers/my_controller.py
from tpsplots.controllers.chart_controller import ChartController

class MyCustomChart(ChartController):
    def my_data_method(self):
        """Return data for YAML charts."""
        # Load and process data
        df = self.load_my_data()

        # Return dict with data arrays
        return {
            "years": df["Year"].values,
            "values": df["Value"].values,
            "labels": ["Label 1", "Label 2"],
            "export_df": df,  # For CSV export
        }
```

Then reference in YAML:

```yaml
data:
  source: my_controller.my_data_method
  # Optional: load a local controller file outside the package
  # source: /path/to/custom_controller.py:my_data_method
```

### IDE Autocomplete with JSON Schema

Generate a JSON Schema for IDE support:

```bash
tpsplots --schema > .vscode/tpsplots-schema.json
```

In VS Code, add to `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    ".vscode/tpsplots-schema.json": "yaml/*.yaml"
  }
}
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TPSPLOTS_HEADLESS` | Force headless mode (`1`/`true`) or GUI mode (`0`/`false`) |

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check tpsplots/

# Format code
ruff format tpsplots/
```

---

## License

This project is released under the Business Source License 1.1. See `LICENSE`.
TPS branding (name, logos, and brand assets) is All Rights Reserved; see `NOTICE`.
Poppins fonts are licensed under the SIL Open Font License 1.1.

---

## Author

Casey Dreier - The Planetary Society
