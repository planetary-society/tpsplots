# Stacked Bar Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Stacked bars for showing composition within categories.

## Example

```yaml
data:
  source: data/budget_breakdown.csv

chart:
  type: stacked_bar
  output: budget_stacked
  title: "Budget Breakdown by Year"
  categories: "{{Fiscal Year}}"
  values:
    "Science": "{{Science}}"
    "Exploration": "{{Exploration}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `categories` | any (template ref) | — | Category labels for the axis |
| `values` | any (template ref) | — | Stack segment values (dict or DataFrame) |

## Bar Styling

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `width` | float | — | Bar width as fraction of category spacing (0.0-1.0). Default: 0.8. Only applies to vertical bars; use height for horizontal. For grouped bars, controls individual bar width (default: 0.35) |
| `alpha` | float | — | Bar transparency (0.0 = fully transparent, 1.0 = fully opaque). Default: 1.0 |
| `edgecolor` | str | — | Bar border color. Default: 'white'. Works with linewidth to create visible borders between adjacent bars |
| `linewidth` | float | — | Bar border line width in points. Default: 0.5. Set to 0 to remove borders |
| `show_category_ticks` | bool | — | Show tick marks on the category axis (x for vertical, y for horizontal). Default: False (tick marks hidden, but labels remain visible) |
| `height` | float | — | Bar height as fraction of category spacing (0.0-1.0). Default: 0.8. Only applies to horizontal bars; use width for vertical |
| `orientation` | `"vertical"`, `"horizontal"` | — | Bar orientation: 'vertical' (categories on x, values on y) or 'horizontal' (categories on y, values on x). Default: 'vertical' |

## Colors

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `colors` | list[str] or str | — | Colors for each stack segment or template ref |

## Value Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_values` | bool | — | Display formatted value labels on each bar. Positioned above positive bars / below negative bars (vertical), or right/left (horizontal). Configure with value_format, value_suffix, etc. |
| `value_format` | str | — | Format for value labels: preset name or Python format spec. Presets: 'monetary' -> ',.0f', 'percentage' -> '.1f%' (also formats axis ticks), 'integer' -> '.0f', 'float' -> '.2f'. Or direct spec like ',.0f' |
| `value_prefix` | str | — | Text prepended before each formatted value label. Default: '' (empty). Examples: '$', '~'. Combined with value_suffix for full formatting |
| `value_suffix` | str | — | Text appended after each formatted value label. Examples: ' yrs', ' months', ' B' for billions. Default: empty string |
| `value_offset` | float | — | Distance from bar end to value label in data units. Default: None (auto-calculates as 2% of value axis range). Negative values place labels inside the bar |
| `value_fontsize` | float or str | — | Font size in points for value labels. Default: 0.9x tick_size for bars, 0.8x for stacked/grouped bars |
| `value_color` | str | — | Text color for value labels. Default: 'black' for regular bars, 'white' for stacked bars (contrast on colored segments) |
| `value_weight` | `"normal"`, `"bold"` or str | — | Font weight for value labels: 'normal' or 'bold'. Default: 'bold' for stacked bars, 'normal' for regular/grouped bars |
| `value_threshold` | float | — | Minimum segment size as percentage of bar total to display a value label. Default: 5.0 (segments <5% of total are unlabeled). Set to 0 to label all non-zero segments |

## Stack Totals

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stack_labels` | bool | — | Show total value labels at the end of each stacked bar (above for vertical, right for horizontal). Default: False. Rendered in bold dark_gray at value_fontsize |
| `stack_label_format` | str | — | Format for stack total labels: preset ('monetary', 'percentage', 'integer', 'float') or Python format spec. Default: same as value_format |
| `stack_label_prefix` | str | — | Text prepended before each stack total label. Default: same as value_prefix |
| `stack_label_suffix` | str | — | Text appended after each stack total label. Default: same as value_suffix. Examples: ' B', ' M' |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | list[str] or str | — | Labels for each stack segment or template ref |

## Scale

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scale` | `"billions"`, `"millions"`, `"thousands"`, `"percentage"` or str | — | Scale formatting for the chart value axis: divides by scale factor and appends unit labels (for example 'billions' -> 'B'). Overrides tick_format specs on the value axis |

## Tick Format

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x_tick_format` | str | — | Python format spec for x-axis tick labels on numeric value axes or horizontal bar value axes. Ignored if scale formatting is active |
| `y_tick_format` | str | — | Python format spec for y-axis tick labels on numeric value axes or vertical bar value axes. Ignored if scale formatting is active |
| `category_label_format` | str | — | Formatting for category labels when categories are date-like. Use 'year' to render YYYY, or any strftime format such as '%Y-%m'. Default: auto-detect year-like dates and render readable labels |

## Legend

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `legend` | bool or dict or str | — | Legend display: False to hide, True for default, or dict of ax.legend() kwargs (e.g., {loc: 'upper right', fontsize: 'medium', ncol: 3}) |

## Grid

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `grid` | bool or dict or str | — | Grid display: True/False for default grid, or dict of ax.grid() kwargs (e.g., {alpha: 0.3, linestyle: '--'}). Default depends on chart type |
| `grid_axis` | `"x"`, `"y"`, `"both"` | — | Which axis to show grid lines on: 'x', 'y', or 'both'. Default: 'y' for vertical charts, 'x' for horizontal charts |

## Axis

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_xticks` | bool | — | Show x-axis tick labels and bottom spine on horizontal bar charts. Default: True for horizontal charts. Not supported for vertical charts |
| `show_yticks` | bool | — | Show y-axis tick labels and left spine on vertical bar charts. Default: True for vertical charts. Not supported for horizontal charts |
| `xlim` | list or dict or str | — | X-axis limits as [min, max], {left: val, right: val}, or template ref |
| `ylim` | list or dict or str | — | Y-axis limits as [min, max], {bottom: val, top: val}, or template ref |
| `xlabel` | str | — | X-axis label text |
| `ylabel` | str | — | Y-axis label text |
| `tick_rotation` | float | — | Rotation angle in degrees for x-axis tick labels. Default: 45 for vertical bars, 0 for horizontal bars and line charts. Scaled to 80% on mobile |
| `tick_size` | float or str | — | Font size in points for axis tick labels. Default: from style (typically 12pt). Scaled to 80% on mobile. Applied to both x and y axes |
| `label_size` | float or str | — | Font size in points for axis labels (xlabel/ylabel). Default: from style (typically 20pt). Scaled to 60% on mobile. Does not affect tick label size |

## Advanced

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bottom_values` | list | — | Custom bottom values for stacking (advanced use) |

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
