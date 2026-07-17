# Line Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Time-series and trend lines. Most common chart type for budget data.

## Example

```yaml
data:
  source: data/budget.csv

chart:
  type: line
  output: budget_trend
  title: "NASA Budget Over Time"
  x: "{{Fiscal Year}}"
  y: "{{Budget}}"
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x` | any (template ref) | — | X-axis data or column reference |
| `y` | any (template ref) | — | Y-axis data or column reference(s) |
| `y_right` | any (template ref) | — | Right y-axis data binding: column reference(s) for secondary axis. Per-series styling arrays (color, labels, etc.) span both axes in [left..., right...] order |

## Line Styling

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `color` | str or list[str] | — | Line color(s) |
| `linestyle` | str or list[str] | — | Line style(s) |
| `linewidth` | float or list[float] | — | Line width(s) |
| `marker` | str or list[str] | — | Marker style(s) |
| `markersize` | float or list[float] | — | Marker size(s): single value or per-series list |
| `alpha` | float or list[float] | — | Line transparency (0.0 = fully transparent, 1.0 = fully opaque). Single value applies to all lines; list sets per-series transparency |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | str or list[str] | — | Legend label(s) |
| `series_types` | list[str] or str | — | Semantic series types that apply default styling per series. Values: 'prior' (gray dashed, 1.5pt), 'average' (blue solid, 4pt, circle markers), 'current' (Rocket Flame solid, 4pt, circle markers). List length must match number of y series. May also be a template ref like '{{series_types}}'. Overridden by explicit color/linestyle/etc. |
| `direct_line_labels` | bool or [DirectLineLabelsConfig](#directlinelabelsconfig) or dict | — | Place labels near line endpoints instead of a legend box. Default: False (use legend). True: enable with auto-positioning. Dict config keys: position ('right'\|'left'\|'top'\|'bottom'\|'auto', default 'auto'), bbox (background box, default True), fontsize (default from style legend_size), end_point (True for default circle marker, dict for custom {marker, size, facecolor, edgecolor, edgewidth, zorder}, or list for per-series config) |

## Reference Lines

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hlines` | float or list or dict | — | Y-values for horizontal reference lines |
| `hline_colors` | str or list[str] | — | Colors for horizontal lines |
| `hline_styles` | str or list[str] | — | Line styles for horizontal lines |
| `hline_widths` | float or list[float] | — | Line widths for horizontal lines |
| `hline_labels` | str or list[str] | — | Labels for horizontal lines |
| `hline_alpha` | float or list[float] | — | Transparency for horizontal lines (0.0-1.0). Default: 0.7. Single value or list matching hlines length |
| `hline_label_position` | `"right"`, `"left"`, `"center"` | — | Horizontal position for hline labels on the plot. Default: 'right'. Labels auto-adjust vertically to prevent overlap |
| `hline_label_offset` | float | — | Horizontal offset for hline labels as fraction of plot width. Default: 0.02 (2% inset from the edge specified by hline_label_position) |
| `hline_label_fontsize` | int or float | — | Font size for horizontal line labels |
| `hline_label_bbox` | bool | — | Add a white rounded background box with colored border to horizontal line labels. Default: True. Helps readability when labels overlap data |

## Scale

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scale` | `"billions"`, `"millions"`, `"thousands"`, `"percentage"` or str | — | Scale formatting for values: divides by scale factor and appends unit label (e.g., 'billions' divides by 1e9 and shows 'B'). Applied to value axis by default. Overrides tick_format specs |
| `axis_scale` | `"x"`, `"y"`, `"both"` | — | Which axis to apply scale formatting to: 'x', 'y', or 'both'. Default: 'y'. For horizontal bars, the value axis is 'x' |

## Right Y-Axis

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ylim_right` | list or dict or str | — | Right y-axis limits |
| `ylabel_right` | str | — | Right y-axis label text |
| `y_tick_format_right` | str | — | Python format spec for right y-axis tick labels. Ignored if scale_right formatting is active |
| `scale_right` | `"billions"`, `"millions"`, `"thousands"`, `"percentage"` or str | — | Scale formatting for right y-axis values |

## Tick Format

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x_tick_format` | str | — | Python format spec for x-axis tick labels (e.g., '.0f', ',.0f'). Applied via FuncFormatter. Ignored if scale formatting is active |
| `y_tick_format` | str | — | Python format spec for y-axis tick labels (e.g., '.0f', ',.0f'). Applied via FuncFormatter. Ignored if scale formatting is active |
| `fiscal_year_ticks` | bool | — | Format x-axis ticks as fiscal years using date formatting. Default: True if x-axis data contains dates. Auto-adjusts density: all years if <10yr range, every 5yr if <20yr, decades if >20yr |
| `max_xticks` | int or str | — | Maximum number of x-axis ticks. For numeric axes, uses MaxNLocator. For categorical axes, calculates step = len(categories) // max_xticks + 1 |
| `integer_xticks` | bool | — | Control integer-only x-axis ticks for numeric axes. None (default): auto-detects — uses integer ticks when all x values are integer-valued. True: always use integer ticks. False: allow fractional steps (disables auto-detection). |

## Custom Ticks

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `xticks` | list | — | Custom x-axis tick positions |
| `xticklabels` | list[str] | — | Custom x-axis tick labels |

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
| `annotations` | list[[ChartAnnotation](#chartannotation)] | — | Data-space text callouts drawn on the primary axes after the chart is rendered. Each item anchors at (x, y) in data coordinates. |
| `data` | any (template ref) | — | DataFrame reference |
| `series_overrides` | dict[int, dict or [SeriesConfig](#seriesconfig)] | — | Per-series override configs (auto-collected from series_N keys) |

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

## Sub-models

### ChartAnnotation

A single text callout anchored in data coordinates.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x` | float or str | **required** | Anchor x position in data coordinates |
| `y` | float | **required** | Anchor y position in data coordinates |
| `text` | str | **required** | Callout text. May contain flexitext style tags to emphasise a phrase, e.g. '<weight:semibold>$43B</> peak'; plain strings render as plain text. |
| `text_x` | float or str | — | Optional x position for the text box (defaults to the anchor) |
| `text_y` | float | — | Optional y position for the text box (defaults to the anchor) |
| `arrow` | bool | `false` | Draw a thin curved connector from the box to the anchor point |
| `color` | str | — | Box border and arrow colour (hex or TPS colour name). Defaults to a quiet grey; the text ink stays the standard annotation colour. |

### DirectLineLabelsConfig

Configuration for direct line labels (placed near line endpoints).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `position` | `"right"`, `"left"`, `"top"`, `"bottom"`, `"above"`, `"below"`, `"auto"` | `"auto"` | Label position relative to line endpoint |
| `bbox` | bool | `true` | Add background box to labels |
| `fontsize` | int or float | — | Font size for labels |
| `end_point` | bool or dict or list | — | Endpoint marker config: True for default, dict for custom style, or list for per-series config |
| `offset` | list | — | Label offset as [x, y] |

### SeriesConfig

Per-series override configuration (populated from series_0, series_1, etc.).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `color` | str | — | Series color |
| `linestyle` | str | — | Line style |
| `linewidth` | float | — | Line width |
| `marker` | str | — | Marker style |
| `markersize` | float | — | Marker size |
| `label` | str | — | Series label |
| `alpha` | float | — | Transparency |
