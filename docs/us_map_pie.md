# Us Map Pie Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Geographic pie charts overlaid on a U.S. state map.

## Example

```yaml
data:
  source: controller:your_controller.get_state_data

chart:
  type: us_map_pie
  output: state_distribution
  title: "Distribution by State"
  pie_data: "{{state_df}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pie_data` | any (template ref) | — | Dict mapping location names to pie chart data dicts (each with 'values', 'labels', 'colors'). Required unless the column-oriented fields below are provided. |
| `location_column` | str | — | Column name in ``data`` whose values match NASA_CENTERS keys (full names or abbreviations). Rows with blank/null values in this column are dropped from plotted pies. |
| `value_columns` | list[str] | — | Column names in ``data`` to use as pie segment values, one per segment. Length must equal ``labels`` and ``colors``. |
| `labels` | list[str] | — | Legend label for each pie segment; aligned with ``value_columns``. |
| `colors` | list[str] | — | Color for each pie segment; aligned with ``value_columns``. Accepts hex codes or TPS brand names (e.g. 'Neptune Blue'). |

## Pie Sizing

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `pie_size_column` | str | — | Key name in each pie_data entry to use for proportional pie sizing. When set, pie sizes are normalized between min_pie_size and max_pie_size. When omitted, all pies use base_pie_size |
| `base_pie_size` | float | — | Base scatter size for pie charts in points-squared. Default: 800. Automatically scaled 2x for desktop. Used as uniform size when pie_size_column is omitted |
| `max_pie_size` | float | — | Maximum scatter size for proportional pie sizing in points-squared. Default: 1500. Automatically scaled 2x for desktop. Only applies when pie_size_column is set |
| `min_pie_size` | float | — | Minimum scatter size for proportional pie sizing in points-squared. Default: 400. Automatically scaled 2x for desktop. Only applies when pie_size_column is set |

## Pie Display

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_pie_labels` | bool | — | Show labels on pie charts |
| `show_percentages` | bool or list[bool] | — | Show percentage values on pie segments |
| `legend_location` | str | — | Matplotlib legend location (loc). Default: 'lower left' |
| `pie_edge_color` | str | — | Edge color for pie wedges. Default: 'white' |
| `pie_edge_width` | float | — | Edge line width for pie wedges. Default: 0.5 |

## Map Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `custom_locations` | dict[str, any (template ref)] | — | Custom location coordinates to override defaults |
| `show_state_boundaries` | bool | — | Show white state boundary lines on the US map. Default: True. When False, boundaries blend into the gray background for a cleaner look |
| `auto_expand_bounds` | bool | — | Automatically expand figure bounds to fit all pies |
| `padding_factor` | float | — | Extra padding around pies when auto-expanding bounds, as fraction of pie radius. Default: 0 for desktop, 0.15 for mobile. Increase to prevent pies from being clipped at figure edges |

## Offset Lines

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `offset_line_color` | str | — | Color for connecting lines from offset pies |
| `offset_line_style` | str | — | Style for connecting lines |
| `offset_line_width` | float | — | Width for connecting lines |

## Advanced

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data` | any (template ref) | — | DataFrame template reference (e.g. '{{data}}') used with the column-oriented fields below to assemble pie_data from a CSV. Ignored when pie_data is provided directly. |

## Common

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output` | str | **required** | Base filename for chart outputs |
| `title` | str | **required** | Chart title |
| `subtitle` | str | — | Chart subtitle (supports {{variable}} templates) |
| `source` | str | — | Data source attribution |
| `eyebrow` | str | — | Short kicker line rendered above the title (uppercased in code). Desktop-only by default; hidden on mobile/social/video devices. |
| `note` | str | — | Methodology note rendered right-aligned above the source line in the footer. Single line, no wrapping. |
| `figsize` | list[float] | — | Figure size as [width, height] in inches. Default: [16, 10] desktop, [8, 9] mobile, [8, 4.2] social. Affects layout of titles, axes, and label positioning calculations |
| `dpi` | int | — | Dots per inch for output resolution. Also used in pixel-to-point conversions for label placement (1 pt = dpi/72 px) |
| `export_data` | any (template ref) | — | Data for CSV export — either a '{{export_df}}' template reference or a resolved DataFrame after template resolution |
| `matplotlib_config` | dict[str, any (template ref)] | — | Raw matplotlib artist kwargs merged after standard field processing. Keys that overlap with typed fields will override them with a logged warning. The receiving chart renderer documents which matplotlib artist consumes them |
