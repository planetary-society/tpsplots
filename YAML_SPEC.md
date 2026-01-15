# TPS Charts YAML Specification v2.0

This document defines the YAML specification for creating charts in the TPS house style.

## Overview

A TPS chart YAML file has two top-level sections:

```yaml
data:    # Where the data comes from
  ...

chart:   # How to display it
  ...
```

---

## Data Section

The `data:` section defines where chart data originates.

### Data Source String

```yaml
data:
  source: data/budget.csv
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | string | yes | CSV path, CSV URL, or controller method |

### Source Formats

**Local CSV**
```yaml
data:
  source: data/budget.csv
```

**URL CSV (Google Sheets, etc.)**
```yaml
data:
  source: https://docs.google.com/spreadsheets/d/.../export?format=csv
```

**Controller Method (module.method)**
```yaml
data:
  source: nasa_budget_chart.budget_by_year
```

**Local Custom Controller**
```yaml
data:
  source: /path/to/custom_controller.py:budget_by_year
```

### Optional Prefixes

Prefixes are optional but can make intent explicit:

```yaml
data:
  source: csv:data/budget.csv
```

```yaml
data:
  source: url:https://docs.google.com/spreadsheets/d/.../export?format=csv
```

```yaml
data:
  source: controller:nasa_budget_chart.budget_by_year
```

```yaml
data:
  source: controller:/path/to/custom_controller.py:budget_by_year
```

### Resolution Rules

1. `http://` or `https://` → URL CSV
2. `*.py:method` → local custom controller
3. paths containing `/` or `\\` or ending with `.csv` → local CSV
4. otherwise → controller method `module.method` in `tpsplots.controllers`

Controller modules must contain **exactly one** `ChartController` subclass that implements the method.
Controller methods must return a **dict** of values.

---

## Chart Section

The `chart:` section defines chart type, metadata, and visualization parameters.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Chart type (see [Chart Types](#chart-types)) |
| `output` | string | Output filename stem (generates `{output}_desktop.png`, etc.) |
| `title` | string | Chart title |

### Optional Metadata

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `subtitle` | string | none | Subtitle (supports `{{variable}}` substitution) |
| `source` | string | none | Data source attribution |

---

## Data References

Data from the `data:` section is referenced using `{{...}}` syntax.

### Simple Reference

```yaml
x: "{{Year}}"
y: "{{Budget}}"
```

References the `Year` and `Budget` columns/keys from the data.

### Nested Reference (Dot Notation)

```yaml
x: "{{series.x_values}}"
y: "{{metrics.budget.values}}"
```

Accesses nested data structures using dot notation. Arbitrary depth is supported.

### Format Strings

```yaml
subtitle: "Total: {{total:.2f}}"
```

Python format specifications can be appended after a colon:
- `{{value:.2f}}` → two decimal places
- `{{date:%Y}}` → year only from date
- `{{pct:.1%}}` → percentage with one decimal

### Resolution Rules

1. Strings wrapped in `{{...}}` are **always** treated as data references
2. Strings **not** wrapped in `{{...}}` are **always** treated as literals
3. If a reference cannot be resolved, an **error** is raised (strict by default)

---

## Chart Types

### `line` - Line Chart

```yaml
chart:
  type: line
  output: budget_trend
  title: "NASA Budget Over Time"

  x: "{{fiscal_year}}"
  y: "{{budget}}"

  color: NeptuneBlue
  linestyle: solid
  linewidth: 3
  marker: o
```

#### Line Chart Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `x` | reference | required | X-axis data |
| `y` | reference or list | required | Y-axis data (single or multiple series) |
| `color` | color or list | `NeptuneBlue` | Line color(s) |
| `linestyle` | string or list | `solid` | Line style: `solid`, `dashed`, `dotted`, `dashdot` |
| `linewidth` | number or list | `3` | Line width in points |
| `marker` | string or list | none | Marker style: `o`, `s`, `^`, `D`, etc. |
| `label` | string or list | none | Series label(s) for legend |

#### Multi-Series (Inline Shorthand)

For a single series, specify parameters directly:

```yaml
y: "{{budget}}"
color: NeptuneBlue
```

#### Multi-Series (Parallel Arrays)

For multiple series, provide lists for `y` and any styling parameters:

```yaml
y: ["{{current_budget}}", "{{prior_budget}}"]
color: [NeptuneBlue, RocketFlame]
linestyle: [solid, dashed]
label: ["Current", "Prior Year"]
```

#### Direct Line Labels

Label lines directly instead of using a legend:

```yaml
direct_line_labels: true
```

Or with configuration:

```yaml
direct_line_labels:
  fontsize: 10
  position: right    # right, left, or auto
  bbox: true         # background box
```

---

### `bar` - Bar Chart

```yaml
chart:
  type: bar
  output: dev_times
  title: "Development Times"

  categories: "{{Spacecraft}}"
  values: "{{Duration}}"

  orientation: horizontal
  sort_by: value
  show_values: true
```

#### Bar Chart Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `categories` | reference | required | Category labels |
| `values` | reference | required | Bar values |
| `orientation` | string | `vertical` | `vertical` or `horizontal` |
| `sort_by` | string | none | `value`, `category`, or none |
| `sort_ascending` | bool | `false` | Sort direction |
| `show_values` | bool | `false` | Display values on bars |
| `value_format` | string | none | Format spec for values (e.g., `.1f`) |
| `value_suffix` | string | none | Suffix for values (e.g., ` yrs`) |
| `colors` | color list | auto | Per-bar colors |
| `height` | number | `0.8` | Bar height (horizontal) or width (vertical) |

---

### `donut` - Donut Chart

```yaml
chart:
  type: donut
  output: budget_breakdown
  title: "Budget Allocation"

  labels: "{{Category}}"
  values: "{{Amount}}"

  hole_size: 0.4
  show_percentages: true
```

#### Donut Chart Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `labels` | reference | required | Slice labels |
| `values` | reference | required | Slice values |
| `hole_size` | number | `0.4` | Inner hole size (0-1) |
| `show_percentages` | bool | `true` | Show percentage labels |
| `center_text` | string | none | Text in center hole |

---

### `lollipop` - Lollipop Chart

```yaml
chart:
  type: lollipop
  output: timeline
  title: "Development Timeline"

  categories: "{{Spacecraft}}"
  start_values: "{{Start}}"
  end_values: "{{End}}"

  y_axis_position: right
  range_labels: true
```

#### Lollipop Chart Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `categories` | reference | required | Category labels |
| `start_values` | reference | required | Range start values |
| `end_values` | reference | required | Range end values |
| `y_axis_position` | string | `left` | `left` or `right` |
| `hide_y_spine` | bool | `false` | Hide y-axis spine |
| `range_labels` | bool | `false` | Show range values |
| `range_suffix` | string | none | Suffix for range labels |
| `marker_size` | number | `5` | Marker size |
| `line_width` | number | `5` | Connector line width |

---

### `stacked_bar` - Stacked Bar Chart

```yaml
chart:
  type: stacked_bar
  output: budget_components
  title: "Budget Components"

  categories: "{{Year}}"
  values:
    Science: "{{Science}}"
    Exploration: "{{Exploration}}"
  colors:
    - NeptuneBlue
    - PlasmaPurple
```

---

### `waffle` - Waffle Chart

```yaml
chart:
  type: waffle
  output: proportion
  title: "Budget Proportion"

  values:
    Science: "{{Science}}"
    Exploration: "{{Exploration}}"

  rows: 10
  columns: 10
```

---

### `us_map_pie` - US Map with Pie Charts

```yaml
chart:
  type: us_map_pie
  output: state_breakdown
  title: "Spending by State"

  state_data: "{{state_df}}"
  pie_values: "{{category_values}}"
```

---

### `line_subplots` - Multiple Line Subplots

```yaml
chart:
  type: line_subplots
  output: multi_metric
  title: "Multiple Metrics"

  subplot_data:
    - x: "{{Year}}"
      y: "{{Budget}}"
      title: "Budget"
    - x: "{{Year}}"
      y: "{{Headcount}}"
      title: "Headcount"
```

---

## Common Parameters

These parameters are available for all chart types.

### Axis Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `xlim` | `[min, max]` | auto | X-axis limits |
| `ylim` | `[min, max]` | auto | Y-axis limits |
| `xlabel` | string | none | X-axis label text |
| `ylabel` | string | none | Y-axis label text |
| `scale` | string | none | Apply scale formatting |
| `axis_scale` | string | `y` | Which axis to scale (`x`, `y`, or `both`) |

#### Format Options

| Value | Description |
|-------|-------------|
| `billions` | Divide by 1B, suffix "B" |
| `millions` | Divide by 1M, suffix "M" |
| `thousands` | Divide by 1K, suffix "K" |
| `percentage` | Multiply by 100, suffix "%" |

### Typography

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `xlabel_size` | int | device default | X-axis label font size |
| `ylabel_size` | int | device default | Y-axis label font size |
| `tick_size` | int | device default | Tick label font size |
| `legend_size` | int | device default | Legend font size |
| `label_size` | int | device default | General label font size |

### Display Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grid` | bool | `true` | Show grid lines |
| `legend` | bool | `false` | Show legend |

### Data Export

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `export_data` | reference | none | Data to export as CSV |

---

## Colors

Use semantic color names in CamelCase:

| Name | Hex | Usage |
|------|-----|-------|
| `NeptuneBlue` | `#037CC2` | Primary brand color |
| `RocketFlame` | `#FF5D47` | Accent/alert color |
| `PlasmaPurple` | `#643788` | Secondary brand color |
| `MediumNeptune` | `#80BDE0` | Light primary |
| `LightNeptune` | `#BFDEF0` | Lightest primary |
| `MediumPlasma` | `#B19BC3` | Light secondary |
| `LightPlasma` | `#D8CDE1` | Lightest secondary |
| `CraterShadow` | `#414141` | Dark text |
| `LunarSoil` | `#8C8C8C` | Gray |
| `CometDust` | `#C3C3C3` | Light gray |
| `SlushyBrine` | `#F5F5F5` | Background |

Hex codes are also accepted:

```yaml
color: "#037CC2"
```

---

## Complete Examples

### Simple Line Chart

```yaml
data:
  source: data/budget.csv

chart:
  type: line
  output: budget_trend
  title: "NASA Budget Over Time"
  subtitle: "Inflation-adjusted dollars"
  source: "NASA Budget Office"

  x: "{{Year}}"
  y: "{{Budget}}"

  color: NeptuneBlue
  ylabel: "Budget"
  scale: billions

  grid: true
```

### Multi-Series Comparison

```yaml
data:
  source: nasa_budget_chart.budget_comparison

chart:
  type: line
  output: budget_comparison
  title: "Budget Comparison"
  subtitle: "Current vs. prior fiscal year"
  source: "{{source}}"

  x: "{{fiscal_years}}"

  y:
    - "{{current_budget}}"
    - "{{prior_budget}}"
  color: [NeptuneBlue, RocketFlame]
  linestyle: [solid, dashed]
  label: ["FY 2025", "FY 2024"]

  scale: billions
  ylabel: "Cumulative Spending"

  grid: true
  legend: false
  direct_line_labels:
    fontsize: 10
    position: right

  export_data: "{{export_df}}"
```

### Horizontal Bar Chart

```yaml
data:
  source: https://docs.google.com/spreadsheets/d/.../export?format=csv

chart:
  type: bar
  output: development_times
  title: "Spacecraft Development Times"
  subtitle: "Years from contract award to first crewed flight"
  source: "Official Reporting"

  categories: "{{Spacecraft}}"
  values: "{{Duration}}"

  orientation: horizontal
  sort_by: value
  sort_ascending: false

  xlabel: "Years"
  xlim: [0, 20]

  show_values: true
  value_format: ".1f"
  value_suffix: " yrs"

  colors:
    - LunarSoil
    - RocketFlame
    - LunarSoil
    - LunarSoil

  tick_size: 14
  xlabel_size: 14
```

### Donut Chart

```yaml
data:
  source: nasa_budget_chart.major_activities_breakdown

chart:
  type: donut
  output: budget_breakdown
  title: "NASA Budget by Major Activity"
  subtitle: "Fiscal Year {{fiscal_year}}"
  source: "NASA Budget Office"

  labels: "{{activities}}"
  values: "{{amounts}}"

  hole_size: 0.4
  show_percentages: true
  center_text: "FY {{fiscal_year}}"
```

---

## CLI Usage

### Generate Charts

```bash
# Single YAML file
tpsplots chart.yaml

# All YAML files in directory
tpsplots yaml/

# Specify output directory
tpsplots chart.yaml --outdir output/
```

### Validate YAML

```bash
tpsplots chart.yaml --validate
```

### Generate Template

```bash
# Generate line chart template with all parameters
tpsplots --new line > my_chart.yaml

# Available chart types
tpsplots --new bar
tpsplots --new donut
tpsplots --new lollipop
tpsplots --new stacked_bar
tpsplots --new waffle
tpsplots --new us_map_pie
tpsplots --new line_subplots
```

### Verbose Errors

```bash
tpsplots chart.yaml --verbose
```

---

## Output Files

For each YAML file, the following outputs are generated:

| File | Description |
|------|-------------|
| `{output}_desktop.png` | Desktop PNG (16:10, 300 DPI) |
| `{output}_desktop.svg` | Desktop SVG (vector) |
| `{output}_desktop.pptx` | PowerPoint slide |
| `{output}_mobile.png` | Mobile PNG (8:9, 300 DPI) |
| `{output}_mobile.svg` | Mobile SVG (vector) |
| `{output}.csv` | Data export (if `export_data` specified) |

---

## Migration from v1.0

### Key Changes

| v1.0 (old) | v2.0 (new) |
|------------|------------|
| 4 sections: `chart`, `data_source`, `metadata`, `parameters` | 2 sections: `data`, `chart` |
| `type: line_plot` | `type: line` |
| `type: bar_plot` | `type: bar` |
| `data_source: {type: google_sheets, url: ...}` | `data: {source: https://...}` |
| `data_source: {type: csv_file, path: ...}` | `data: {source: data/file.csv}` |
| `output_name: x` | `output: x` |
| `x: Year` (implicit reference) | `x: "{{Year}}"` (explicit reference) |
| `color: "#037CC2"` | `color: NeptuneBlue` |
| Parallel arrays: `y: [A, B]`, `color: [C, D]` | Parallel arrays remain supported |

### Example Migration

**Before (v1.0):**
```yaml
chart:
  type: line_plot
  output_name: budget

data_source:
  type: csv_file
  path: "data/budget.csv"

metadata:
  title: "NASA Budget"
  subtitle: "FY 2025"
  source: "NASA"

parameters:
  x: Year
  y: Budget
  color: "#037CC2"
  scale: billions
  label_size: 14
```

**After (v2.0):**
```yaml
data:
  source: data/budget.csv

chart:
  type: line
  output: budget
  title: "NASA Budget"
  subtitle: "FY 2025"
  source: "NASA"

  x: "{{Year}}"
  y: "{{Budget}}"
  color: NeptuneBlue
  scale: billions
  label_size: 14
```
