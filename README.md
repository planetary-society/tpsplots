# TPS Plots

A data visualization framework for The Planetary Society that creates consistent, branded charts for web and presentations.

## Features

- **YAML-Driven Chart Generation** - Define charts declaratively without writing Python code
- **Interactive Chart Editor** - Browser-based GUI for creating and editing charts with live preview
- **Multiple Chart Types** - Area, line, scatter, bar, donut, treemap, lollipop, stacked bar, waffle, grouped bar, US map pie, and line subplots
- **Automatic Responsive Output** - Generates desktop (16:10), mobile (8:9), and social card (2400x1260, 40:21 OG ratio) versions
- **Multi-Format Export** - SVG, PNG, PPTX, and CSV data export
- **Flexible Data Sources** - Google Sheets, CSV files, or custom controller methods
- **TPS Brand Styling** - Consistent Planetary Society branding with Poppins fonts and a house design language (see below)

## Design Language

Every chart shares one anatomy so TPS output is recognizable at a glance and honest by
construction. The defaults implement all of this — a YAML file gets the house style for
free, and the conventions below explain *when to reach for which option*.

### Anatomy

- **Canvas**: Slushy Brine (`#F5F5F5`) throughout, anchored by a single **2.5pt bottom
  spine** (the "launchpad") — no top, right, or left spines.
- **Grid**: horizontal-only hairlines (`#DBDBDB`, solid, 0.8pt). The grid marks y
  positions, so y-axis tick stubs are suppressed; the x-axis keeps short 4pt ticks. No
  minor ticks anywhere.
- **Header**: optional `eyebrow:` kicker (Neptune Blue, uppercase, desktop only), a
  near-black title, and a gray subtitle. The plot stretches to fill whatever the header
  and footer don't use.
- **Footer**: TPS logo plus a standardized `note:` + `source:` line. Put methodology in
  `note:` — inflation basis, denominators, axis-zero disclosures — not in the subtitle.
- **Legends**: frameless, and only when direct labels can't work. Prefer labeling series
  at their endpoints.

### Color grammar

Hue carries *meaning*, not decoration. Assign colors by role, never by "what's next in
the cycle looks nice":

| Role | Color | When |
|------|-------|------|
| Enacted / actual / primary | `Neptune Blue` `#037CC2` | The series the chart is about |
| Taken away | `Rocket Flame` `#FF5D47` | Cuts, cancellations, at-risk programs. **Reserved** — in composition charts (donut/treemap/waffle) categories stay in blue/purple/gray families so red keeps its meaning |
| Secondary series | `Plasma Purple` `#643788` | A second entity compared against the primary |
| Comparison / tertiary | `Medium Neptune` `#3FA9E0` | Fourth slot in the cycle |
| Context | `Lunar Soil` `#8C8C8C`, `Crater Shadow` `#414141` | Historical background, de-emphasized series |

The automatic series cycle runs in exactly that order and is validated for
colorblind-safe adjacency on the brine canvas. More than six series should fold into a
gray "Other" or become small multiples — never invent a seventh hue.

### Certainty grammar

Color carries valence; **linestyle carries certainty**:

- **Solid** = enacted, appropriated, actual.
- **Dotted** (`:`) = proposed or projected — a budget request, a projection, anything
  not yet law. Dotted lines render as true round dots (the base style tunes
  `lines.dotted_pattern` for this).
- **Gray dashed** (`--`) = prior-year context via `series_types: [prior, ...]`.

A solid red future asserts a proposal as fact; TPS's core subject is proposals, so the
break between solid and dotted should land at the last enacted year.

### Marks

- Lines are **3pt with no per-point markers**. The featured series ends in the TPS
  signature **orbit-ring endpoint** (a filled dot wearing an unfilled ring) with a boxed
  direct label — on by default with direct labels, or explicit via
  `end_point: {marker: ring}`.
- Bars are flat-topped (no rounded ends — they ambiguate the measured value) with value
  labels on the data (`show_values: true`).
- Data outside a configured `xlim` window is clipped from the dataset on line, scatter,
  and subplot charts, so edge markers render whole and the y-axis scales to what is
  visible.

### Takeaway layer

The chart states the takeaway; the reader shouldn't have to derive it:

```yaml
chart:
  eyebrow: "FY 2026 APPROPRIATIONS"        # kicker above the title
  note: "Budget authority in current dollars; marks are not enacted law."
  annotations:                              # callouts in the direct-label box style
    - x: -0.28
      y: 18809100000
      text: "$6B (24%) below\nCongress's marks"
      arrow: true
```

Every highlighted phrase, delta, or annotation must be literal and defensible from the
plotted data — the credibility contract behind all advocacy output.

### Output variants

| Variant | Ratio | Job |
|---------|-------|-----|
| Desktop | 16:10 | Article embeds; full header with eyebrow |
| Mobile | 8:9 | **The direct social-share format** — designed first; eyebrow dropped, titles wrap |
| Social | 40:21 (2400×1260) | Open Graph link preview only — intentionally headline-free, platforms show the page title |

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
  labels: ["Series A", "Series B"]
```

### 2. Generate the Chart

**CLI:**
```bash
tpsplots generate my_chart.yaml
```

**Interactive Editor:**
```bash
tpsplots editor           # Opens a browser-based editor with live preview
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
- `my_first_chart_social.png` (2400x1260 social card, 40:21 OG ratio, PNG only)
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

Track NASA budget over time with inflation adjustment:

```yaml
# nasa_budget_pbr_appropriation_by_year_inflation_adjusted.yaml
data:
  source: nasa_budget_chart.nasa_budget_by_year

chart:
  type: line
  output: nasa_budget_pbr_appropriation_by_year_inflation_adjusted
  title: "NASA's budget from 1959 to {{metadata.max_appropriation_fiscal_year}}"
  subtitle: Adjusted for inflation, NASA's budget has remained relatively steady after the end of Apollo.
  source: "NASA Budget Requests, 1961-{{metadata.max_pbr_fiscal_year}}. Adjusted to {{metadata.inflation_adjusted_year}} USD."

  x: "{{fiscal_year}}"
  y:
    - "{{pbr_adjusted}}"
    - "{{appropriation_adjusted}}"
  color: ["light_blue", "Neptune Blue"]
  linestyle: [":", "-"]
  linewidth: [2.5, 4]
  labels: ["Proposed", "Final"]
  xlim: [1958-01-01, 2030-01-01]
  ylim: [0, 80000000000]
  scale: billions
  legend: false
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
  labels: "{{labels}}"
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
| `area` | Ordinary or stacked filled series | `x`, `y`, `stacked`, `color`, `labels` |
| `line` | Multi-series line charts | `x`, `y`, `color`, `linestyle`, `marker`, `labels` |
| `scatter` | Scatter plots (line chart variant) | `x`, `y`, `color`, `marker`, `labels` |
| `bar` | Vertical or horizontal bars | `categories`, `values`, `orientation`, `colors` |
| `donut` | Donut/pie charts | `values`, `labels`, `hole_size`, `center_text` |
| `treemap` | Space-filling composition charts | `labels`, `values`, `colors`, `show_percentages` |
| `lollipop` | Timeline/range visualization | `categories`, `start_values`, `end_values`, `colors` |
| `stacked_bar` | Stacked bar charts | `categories`, `values`, `colors` |
| `waffle` | Waffle/grid charts | `values`, `labels`, `rows`, `columns` |
| `grouped_bar` | Side-by-side grouped bars | `categories`, `groups`, `width`, `colors` |
| `us_map_pie` | US map with pie overlays | `state_data`, `pie_values` |
| `line_subplots` | Multiple subplot panels (CLI only) | `subplot_data`, `grid_shape` |

List all available types: `tpsplots --list-types`

---

## Animated Charts (`tpsplots animate`)

Turn a static chart into a short MP4 of it building itself out — lines and areas revealing left-to-right with smooth easing, bars growing from the baseline in a staggered cascade, labels settling into place. These are made for Instagram and YouTube, where a chart that animates on autoplay stops the scroll.

The continuous-series and bar families animate today: `area`, `line`, `scatter`, `bar`, `grouped_bar`, `stacked_bar`, and `lollipop`. Other chart types report a clear "not animatable" message and the batch continues. Each run writes `{output}_{format}.mp4` plus a poster PNG of the final frame. The default output is a **square 1080×1080** video; use `--format` for landscape (1920×1080), portrait (1080×1920), or `all` for every aspect at once.

**The video is the chart panel only** — no title, subtitle, source line, or logo. Titles and branding are composited in your video editor, which is what lets the same chart work cropped to square, landscape, and portrait.

```bash
# Square 1080×1080 (default)
tpsplots animate yaml/chart.yaml

# Every aspect ratio at once
tpsplots animate --format all yaml/chart.yaml

# 4K landscape for YouTube (super-samples the encode)
tpsplots animate --scale 2 --format landscape yaml/chart.yaml
```

Tune the motion per chart with an optional top-level `animation:` block. Any value here is overridden by the matching CLI flag when it is passed, and falls back to a built-in default when it is not:

```yaml
animation:
  formats: [square, landscape]   # square | landscape | portrait | all
  fps: 60                        # draft quality caps this at 30
  duration: 2.0                  # draw-phase length in seconds
  easing: cubic_in_out           # e.g. cubic_in_out (default), quint_out, glide_pop
  end_hold: 3.0                  # seconds to hold on the final frame
```

### Installation

Encoding needs an ffmpeg binary. Install the optional extra to bundle a private one:

```bash
uv sync --extra animate          # or: pip install 'tpsplots[animate]'
```

The bundled `imageio-ffmpeg` binary is GPL-licensed; tpsplots only invokes it as a subprocess, so it carries no licensing impact for tpsplots itself. A system ffmpeg (`brew install ffmpeg`) works too.

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
- Currency columns (e.g., `$42,013`) are auto-cleaned to numeric values

### CSV Files (Local Data)

Load from a local CSV file:

```yaml
data:
  source: data/my_data.csv
```

### Data Source Parameters

Customize data loading with optional `params`:

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv
  params:
    columns:                    # Keep only these columns
      - "Fiscal Year"
      - "Amount"
    cast:                       # Convert column types
      Fiscal Year: int
      Amount: float
    renames:                    # Rename columns
      "Old Name": "New Name"
    auto_clean_currency: true   # Auto-detect and clean $X,XXX columns (default for URLs)
```

### Inflation Adjustment

Apply inflation adjustment to columns directly from YAML:

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv
  calculate_inflation:
    columns:                    # Columns to adjust
      - "Apollo"
      - "Artemis"
    type: nnsi                  # "nnsi" (default) or "gdp"
    fiscal_year_column: "Fiscal Year"  # Column with fiscal years
    target_year: 2025           # Target FY (auto-calculated if omitted)
```

Creates new columns named `{column}_adjusted_{type}` (e.g., `Apollo_adjusted_nnsi`).

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

Use TPS brand color names instead of hex codes. The automatic series cycle runs in this
order (see [Design Language](#design-language) for when each role applies):

| Name | Hex | Role |
|------|-----|------|
| `NeptuneBlue` | `#037CC2` | Primary — enacted / actual |
| `RocketFlame` | `#FF5D47` | Taken away — cuts, cancellations (reserved in composition charts) |
| `PlasmaPurple` | `#643788` | Secondary series |
| `MediumNeptune` | `#3FA9E0` | Comparison / tertiary |
| `LunarSoil` | `#8C8C8C` | Context gray |
| `CraterShadow` | `#414141` | Dark context / text ink |

Full palette in `tpsplots/colors.py`.

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
| `-q, --quiet` | Suppress progress output |
| `--verbose` | Enable verbose/debug logging |

#### `validate` - Validate Configuration

```bash
tpsplots validate [OPTIONS] INPUTS...
```

| Option | Description |
|--------|-------------|
| `-q, --quiet` | Suppress progress output |
| `--verbose` | Enable verbose/debug logging |

#### `editor` - Interactive Chart Editor

```bash
tpsplots editor [OPTIONS] [YAML_DIR]
```

| Option | Description |
|--------|-------------|
| `YAML_DIR` | Directory containing YAML chart configs (default: `yaml/`) |
| `--host TEXT` | Host interface (default: `127.0.0.1`) |
| `--port INT` | Port for the editor server (default: auto-select) |
| `--open-browser/--no-open-browser` | Auto-open in browser (default: on) |

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

# Launch the interactive chart editor
tpsplots editor yaml/

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
├── commands/                # CLI subcommands (editor, etc.)
├── editor/                  # Interactive chart editor
│   ├── app.py               # Starlette ASGI app
│   ├── session.py           # EditorSession: YAML ↔ form state
│   ├── ui_schema.py         # JSON Schema / uiSchema generation
│   ├── routes/              # API endpoints (schema, preview, files, data)
│   ├── static/              # Frontend (React 19, htm, CSS)
│   └── templates/           # HTML shell
├── controllers/             # Chart generation logic
│   ├── nasa_budget_chart.py
│   ├── fy2025_charts.py
│   └── ...
├── data_sources/            # Data loading and processing
│   ├── google_sheets_source.py
│   ├── nasa_budget_data_source.py
│   └── ...
├── models/                  # Pydantic validation models
│   ├── chart_config.py      # ChartConfig discriminated union
│   ├── charts/              # Per-chart-type config models
│   │   ├── line.py          # LineChartConfig, SeriesConfig, etc.
│   │   ├── bar.py           # BarChartConfig
│   │   ├── donut.py         # DonutChartConfig
│   │   └── ...              # One file per chart type
│   ├── mixins/              # Shared field groups
│   │   ├── base.py          # ChartConfigBase (common fields)
│   │   ├── shared.py        # SharedFieldsMixin (axes, grid, ticks)
│   │   └── bar.py           # BarFieldsMixin (bar-specific styling)
│   ├── data_sources.py
│   ├── parameters.py
│   └── yaml_config.py
├── processors/              # YAML processing pipeline
│   ├── yaml_chart_processor.py
│   ├── render_pipeline.py   # Shared render context (CLI + editor)
│   └── resolvers/           # Data, parameter, metadata resolution
├── templates/               # Chart type templates for --new
├── utils/                   # Shared utilities
│   ├── currency_processing.py
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
uv sync --extra dev

# Run tests
pytest

# Run linting
ruff check tpsplots/

# Format code
ruff format tpsplots/
```

### Config/View Sync

Each chart view has a `CONFIG_CLASS` linking it to its Pydantic config model. The test at `tests/test_config_view_sync.py` uses AST analysis to verify every `kwargs.pop("key")` in view code has a matching config model field. This prevents configuration drift between models and rendering code. Run it with:

```bash
pytest tests/test_config_view_sync.py -v
```

---

## License

This project is released under the Business Source License 1.1. See `LICENSE`.
TPS branding (name, logos, and brand assets) is All Rights Reserved; see `NOTICE`.
Poppins fonts are licensed under the SIL Open Font License 1.1.

---

## Author

Casey Dreier - The Planetary Society
