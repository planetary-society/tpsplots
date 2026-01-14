# TPS Plots

A data visualization framework for The Planetary Society that creates consistent, branded charts for web and presentations.

## Features

- **YAML-Driven Chart Generation** - Define charts declaratively without writing Python code
- **Multiple Chart Types** - Line, bar, lollipop, donut, waffle, stacked bar, and more
- **Automatic Responsive Output** - Generates both desktop (16:9) and mobile (1:1) versions
- **Multi-Format Export** - SVG, PNG, PPTX, and CSV data export
- **Flexible Data Sources** - Google Sheets, CSV files, or custom controller methods
- **TPS Brand Styling** - Consistent Planetary Society branding with Poppins fonts
- **Headless Support** - Auto-detects CI/CD environments for server-side generation
- **JSON Schema** - IDE autocomplete support for YAML configurations

## Installation

```bash
# Install from git repository
pip install git+https://github.com/planetary/tpsplots.git

# Or install in development mode
git clone https://github.com/planetary/tpsplots.git
cd tpsplots
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a YAML Configuration

```yaml
# my_chart.yaml
chart:
  type: line_plot
  output_name: my_first_chart

data_source:
  type: google_sheets
  url: "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/export?format=csv"

metadata:
  title: "My Chart Title"
  subtitle: "A descriptive subtitle for context"
  source: "Data Source Attribution"

parameters:
  x: Year
  y: [Value1, Value2]
  color: ["#037CC2", "#FF5D47"]
  label: ["Series A", "Series B"]
```

### 2. Generate the Chart

**CLI:**
```bash
tpsplots my_chart.yaml
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

## Real-World Examples

### Example 1: Line Chart with Historical Data

Track NASA budget over time with projections:

```yaml
# nasa_budget_by_year_with_projection.yaml
chart:
  type: line_plot
  output_name: nasa_budget_by_year_with_projection_inflation_adjusted

data_source:
  type: controller_method
  class: tpsplots.controllers.nasa_budget_chart.NASABudgetChart
  method: nasa_budget_by_year_with_projection_inflation_adjusted

metadata:
  title: How NASA's budget has changed over time
  subtitle: After its peak during Apollo, NASA's inflation-adjusted budget has held
    relatively steady, though that may change.
  source: NASA Budget Requests

parameters:
  x: fiscal_years
  y:
    - appropriation_adjusted_nnsi
    - white_house_budget_projection
  color: ["#037CC2", "#FF5D47"]
  linestyle: ["-", "-"]
  marker: ["", "o"]
  label: ["", "Proposed"]
  xlim: xlim
  ylim: ylim
  scale: billions
  legend: legend
  export_data: export_df
```

### Example 2: Horizontal Bar Chart from Google Sheets

Compare spacecraft development timelines with data from a Google Sheet:

```yaml
# human_spacecraft_dev_times.yaml
chart:
  type: bar_plot
  output_name: human_spaceflight_development_comparisons

data_source:
  type: google_sheets
  url: "https://docs.google.com/spreadsheets/d/1uYSirJmE0gLQ701iBFZASsTQL0od36l9xJ7jbEagnrY/export?format=csv"

metadata:
  title: "A five year sprint to the Moon?"
  subtitle: "A new entrant to provide crewed landings for NASA's Artemis program
    by 2030 has five years to design and build their spacecraft."
  source: "Official Reporting. Details: planet.ly/hsfdevtimes"

parameters:
  categories: Spacecraft
  values: Duration (years)
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
    - "#8C8C8C"  # Mercury
    - "#8C8C8C"  # Gemini
    - "#8C8C8C"  # Apollo CSM
    - "#8C8C8C"  # Apollo LM
    - "#8C8C8C"  # Shuttle Orbiter
    - "#8C8C8C"  # Orion
    - "#8C8C8C"  # Crew Dragon
    - "#8C8C8C"  # Starliner
    - "#8C8C8C"  # Starship HLS
    - "#8C8C8C"  # Blue Moon
    - "#FF5D47"  # New HLS Entrant (highlighted)
```

### Example 3: Lollipop Chart with Timeline Ranges

Visualize development periods with start and end dates:

```yaml
# human_spaceflight_development_times.yaml
chart:
  type: lollipop_plot
  output_name: human_spaceflight_development_comparisons

data_source:
  type: google_sheets
  url: "https://docs.google.com/spreadsheets/d/1uYSirJmE0gLQ701iBFZASsTQL0od36l9xJ7jbEagnrY/export?format=csv"

metadata:
  title: "Human Spaceflight Development Times Comparison"
  subtitle: "To make a 2030 landing deadline, a new human landing spacecraft would
    need be the fastest program development in 65 years."
  source: "NASA Historical Data"

parameters:
  categories: Spacecraft
  start_values: Start Date_year      # Auto-rounded from date column
  end_values: First Crewed Utilization_year
  xlim: [1959, 2031]
  y_axis_position: right
  hide_y_spine: true

  # Color by era: blue for historical, purple for future
  colors:
    - "#0B3D91"  # Mercury through Starliner (historical)
    - "#0B3D91"
    - "#0B3D91"
    - "#0B3D91"
    - "#0B3D91"
    - "#0B3D91"
    - "#0B3D91"
    - "#0B3D91"
    - "#643788"  # Future HLS projects
    - "#643788"
    - "#643788"

  # Solid for completed, dotted for projected
  linestyle: ["-", "-", "-", "-", "-", "-", "-", "-", ":", ":", ":"]

  marker_size: 5
  line_width: 5
  grid: true
  grid_axis: x
  range_labels: true
  range_suffix: " yrs"
  export_data: data
```

### Example 4: Donut Chart for Budget Breakdown

Show NASA budget allocation by directorate:

```yaml
# nasa_major_activities_donut.yaml
chart:
  type: donut_plot
  output_name: nasa_directorate_breakdown_donut_chart

data_source:
  type: controller_method
  class: tpsplots.controllers.nasa_budget_chart.NASABudgetChart
  method: nasa_major_activites_donut_chart

metadata:
  title: NASA's budget is subdivided by mission area
  subtitle: "Directorates are responsible for distinct activities — from science
    to facilities — and they don't share funding."
  source: NASA FY2025 Budget Request

parameters:
  values: sorted_values
  labels: sorted_labels
  show_percentages: true
  label_distance: 1.1
  hole_size: 0.6
  center_text: NASA
  center_color: white
  export_data: export_df
```

### Example 5: Multi-Series Comparison with Direct Labels

Compare contract awards across fiscal years:

```yaml
# fy2025_new_contracts_comparison.yaml
chart:
  type: line_plot
  output_name: new_contracts_historical_comparison

data_source:
  type: controller_method
  class: tpsplots.controllers.fy2025_charts.FY2025Charts
  method: new_contract_awards_comparison_to_prior_years

metadata:
  title: "NASA's total new contract awards in FY 2025"
  subtitle: "While below the recent average, the total number was similar to that in 2024."
  source: "USASpending.gov (Does not include IDVs)"

parameters:
  x: months
  y: y_series
  color: colors
  linestyle: linestyles
  linewidth: linewidths
  marker: markers
  label: labels
  ylim: [0, 6000]
  ylabel: "Cumulative New Contracts Awarded"
  label_size: 13
  tick_size: 14
  grid: true
  legend: false
  direct_line_labels:
    fontsize: 10
  export_data: export_df
```

---

## Chart Types Reference

| Type | Description | Key Parameters |
|------|-------------|----------------|
| `line_plot` | Multi-series line charts | `x`, `y`, `color`, `linestyle`, `marker`, `label` |
| `bar_plot` | Vertical or horizontal bars | `categories`, `values`, `orientation`, `colors` |
| `lollipop_plot` | Timeline/range visualization | `categories`, `start_values`, `end_values`, `colors` |
| `donut_plot` | Donut/pie charts | `values`, `labels`, `hole_size`, `center_text` |
| `stacked_bar_plot` | Stacked bar charts | `categories`, `series`, `colors` |
| `waffle_plot` | Waffle/grid charts | `values`, `labels`, `rows`, `columns` |
| `us_map_pie_plot` | US map with pie overlays | `state_data`, `pie_values` |
| `line_subplots_plot` | Multiple subplot panels | `x`, `y_list`, `subplot_titles` |

List all available types: `tpsplots --list-types`

---

## Data Sources

### Google Sheets (Recommended for Collaboration)

Fetch data directly from a public Google Sheet:

```yaml
data_source:
  type: google_sheets
  url: "https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv"
```

**Tips:**
- Sheet must be publicly accessible or "Anyone with link can view"
- Use the `/export?format=csv` URL format
- For specific sheets/tabs, add `&gid=SHEET_GID`

### CSV Files (Local Data)

Load from a local CSV file:

```yaml
data_source:
  type: csv_file
  path: data/my_data.csv
```

### Controller Methods (Complex Data Processing)

Use existing Python controllers for advanced data manipulation:

```yaml
data_source:
  type: controller_method
  class: tpsplots.controllers.nasa_budget_chart.NASABudgetChart
  method: nasa_budget_by_year_inflation_adjusted
```

If the controller lives outside your Python path, provide a local file path:

```yaml
data_source:
  type: controller_method
  class: MyCustomChart
  method: my_data_method
  path: "/path/to/custom_controller.py"
```

**Available Controllers:**
- `tpsplots.controllers.nasa_budget_chart.NASABudgetChart` - NASA budget analysis
- `tpsplots.controllers.fy2025_charts.FY2025Charts` / `tpsplots.controllers.fy2026_charts.FY2026Charts`
- `tpsplots.controllers.china_comparisons_controller.ChinaComparisonsController`
- `tpsplots.controllers.mission_spending_controller.MissionSpendingController`

---

## CLI Reference

```bash
tpsplots [OPTIONS] [INPUTS]

Arguments:
  INPUTS              YAML file(s) or directory(ies) to process

Options:
  -o, --outdir PATH   Output directory (default: charts/)
  --validate          Validate YAML without generating charts
  --strict            Error on unresolved data references
  -q, --quiet         Suppress progress output
  --verbose           Enable debug logging
  --schema            Print JSON Schema for IDE autocomplete
  --list-types        List available chart types
  --version           Show version and exit
  --help              Show help message
```

**Examples:**

```bash
# Generate single chart
tpsplots yaml/my_chart.yaml

# Process entire directory
tpsplots yaml/

# Validate without generating
tpsplots --validate yaml/my_chart.yaml

# Custom output directory
tpsplots -o output/ yaml/

# Generate JSON Schema for IDE support
tpsplots --schema > tpsplots-schema.json
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
data_source:
  type: controller_method
  class: myproject.my_controller.MyCustomChart
  method: my_data_method
  # Optional: load a local controller file outside the package
  # path: "/path/to/custom_controller.py"
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

## Author

Casey Dreier - The Planetary Society
