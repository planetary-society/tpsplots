# Donut Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Proportional donut charts for showing composition.

## Example

```yaml
data:
  source: data/directorates.csv

chart:
  type: donut
  output: budget_donut
  title: "NASA Budget Composition"
  labels: "{{Directorate}}"
  values: "{{Budget}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `values` | any (template ref) | — | Values for each donut segment |
| `labels` | any (template ref) | — | Labels for each segment |

## Colors

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `colors` | list[str] | — | Colors for each segment |

## Donut Shape

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hole_size` | float | — | Relative size of donut hole as fraction of pie radius (0.0-1.0). Default: 0.7. Set to 0 for a solid pie chart, 1.0 for a thin ring |
| `center_text` | str | — | Text displayed in the center of the donut hole. Rendered at title_size with bold weight. Typically used for totals or key metrics |
| `center_color` | str | — | Fill color of the center circle (donut hole). Default: light_gray (#D3D3D3). Accepts any matplotlib color or TPS brand name |
| `wedgeprops` | dict[str, any (template ref)] | — | Properties for pie wedges (linewidth, edgecolor, etc.) |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_percentages` | bool | — | Show percentage values alongside each segment label (e.g., 'Science\n(25.0%)'). Default: True. Percentages are auto-calculated from values |
| `label_wrap_length` | int | — | Maximum characters per line for segment labels before word-wrapping. Default: from style (typically 15). Labels wrap on word boundaries |
| `label_distance` | float | — | Distance of segment labels from chart center in plot units. Default: 1.4 (placed outside the pie radius). Increase to push labels further out if they overlap segments |

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
