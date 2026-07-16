# Treemap Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Space-filling proportional charts for showing a flat composition.

## Example

```yaml
data:
  source: data/composition.csv

chart:
  type: treemap
  output: budget_treemap
  title: "Budget Composition"
  labels: "{{Category}}"
  values: "{{Amount}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | any (template ref) | — | Labels for each treemap tile |
| `values` | any (template ref) | — | Positive values determining treemap tile areas |

## Colors

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `colors` | str or list[str] | — | Tile color or colors, using matplotlib or TPS brand names |

## Treemap Tiles

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `edgecolor` | str | `"Polar White"` | Tile border color |
| `linewidth` | float | `2.0` | Tile border width in points |
| `alpha` | float | `1.0` | Tile opacity |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_labels` | bool | `true` | Show category labels inside fitting tiles |
| `show_values` | bool | `false` | Show formatted values inside fitting tiles |
| `show_percentages` | bool | `true` | Show each category's percentage of the total |
| `value_format` | str | `"float"` | Format for displayed values: preset ('monetary', 'percentage', 'integer', 'float') or Python format spec |
| `label_min_area_pct` | float | `1.0` | Minimum total-area percentage eligible for an internal label |
| `label_wrap_length` | int | — | Maximum characters per line; defaults to the device style |
| `label_fontsize` | float | — | Label size in points; defaults to the device style |

## Common

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output` | str | **required** | Base filename for chart outputs |
| `title` | str | **required** | Chart title |
| `subtitle` | str | — | Chart subtitle (supports {{variable}} templates) |
| `source` | str | — | Data source attribution |
| `figsize` | list[float] | — | Figure size as [width, height] in inches. Default: [16, 10] desktop, [8, 9] mobile, [8, 4.2] social. Affects layout of titles, axes, and label positioning calculations |
| `dpi` | int | — | Dots per inch for output resolution. Also used in pixel-to-point conversions for label placement (1 pt = dpi/72 px) |
| `export_data` | any (template ref) | — | Data for CSV export — either a '{{export_df}}' template reference or a resolved DataFrame after template resolution |
| `matplotlib_config` | dict[str, any (template ref)] | — | Raw matplotlib artist kwargs merged after standard field processing. Keys that overlap with typed fields will override them with a logged warning. The receiving chart renderer documents which matplotlib artist consumes them |
