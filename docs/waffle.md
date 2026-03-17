# Waffle Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Waffle charts for part-of-whole visualisation.

## Example

```yaml
data:
  source: data/composition.csv

chart:
  type: waffle
  output: budget_waffle
  title: "Budget Composition"
  values:
    "Science": "{{Science}}"
    "Exploration": "{{Exploration}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `values` | any (template ref) | — | Dict or list of values for waffle blocks |

## Colors

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `colors` | list[str] | — | Colors for each category |

## Waffle Grid

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rows` | int | — | Number of rows in the waffle grid. Default: auto-calculated from total blocks and figure aspect ratio. If neither rows nor columns is set, both are computed to fit the figsize |
| `columns` | int | — | Number of columns in the waffle grid. Default: auto-calculated from total blocks and figure aspect ratio. If neither rows nor columns is set, both are computed to fit the figsize |
| `vertical` | bool | — | Stack blocks vertically (column-first) instead of horizontally (row-first). Passed directly to pywaffle.Waffle |
| `starting_location` | `"NW"`, `"NE"`, `"SW"`, `"SE"` or str | — | Corner where block filling begins. Values: 'NW' (top-left), 'NE' (top-right), 'SW' (bottom-left), 'SE' (bottom-right). Passed directly to pywaffle.Waffle |
| `interval_ratio_x` | float | — | Horizontal gap between waffle blocks as ratio of block width. Default: pywaffle default (0.2). Increase for more spacing |
| `interval_ratio_y` | float | — | Vertical gap between waffle blocks as ratio of block height. Default: pywaffle default (0.2). Increase for more spacing |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | list[str] or str | — | Labels for legend or template ref |

## Legend

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `legend` | bool or dict or str | — | Legend display: False to hide, True for default, or dict of ax.legend() kwargs (e.g., {loc: 'upper right', fontsize: 'medium', ncol: 3}) |

## Advanced

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pywaffle_config` | dict[str, any (template ref)] | — | Raw kwargs passed through to pywaffle.Waffle for less-common parameters (icon_style, icon_legend, block_arranging_style, etc.) |

## Common

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output` | str | **required** | Base filename for chart outputs |
| `title` | str | **required** | Chart title |
| `subtitle` | str | — | Chart subtitle (supports {{variable}} templates) |
| `source` | str | — | Data source attribution |
| `figsize` | list[float] | — | Figure size as [width, height] in inches. Default: [16, 10] desktop, [9, 16] mobile. Affects layout of titles, axes, and label positioning calculations |
| `dpi` | int | — | Dots per inch for output resolution. Also used in pixel-to-point conversions for label placement (1 pt = dpi/72 px) |
| `export_data` | any (template ref) | — | Data for CSV export — either a '{{export_df}}' template reference or a resolved DataFrame after template resolution |
| `matplotlib_config` | dict[str, any (template ref)] | — | Raw matplotlib kwargs merged into the plot call after standard field processing. Keys that overlap with typed fields will override them with a logged warning. Donut: passed to ax.pie(); line/scatter: passed to ax.plot(); bar: passed to ax.bar() |
