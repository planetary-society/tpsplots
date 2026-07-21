# Area Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Filled time-series charts for showing totals or composition over time.

## Example

```yaml
data:
  source: data/budget_composition.csv

chart:
  type: area
  output: budget_composition
  title: "Budget Composition"
  x: "{{Fiscal Year}}"
  y: ["{{Science}}", "{{Exploration}}"]
  stacked: true
  color: [Neptune Blue, Rocket Flame]
  labels: ["Science", "Exploration"]
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x` | any (template ref) | — | X-axis data or column reference |
| `y` | any (template ref) | — | Y-axis data or column reference(s) |

## Area Styling

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stacked` | bool | `false` | Stack series cumulatively from a zero baseline |
| `color` | str or list[str] | — | Area fill color(s) |
| `alpha` | float or list[float] | — | Area opacity: scalar or per-series list; defaults to 0.65 for ordinary areas and 1.0 for stacked areas |
| `edgecolor` | str or list[str] | `"none"` | Closed polygon perimeter color(s); defaults to "none" |
| `linewidth` | float or list[float] | `0.0` | Closed polygon perimeter width(s); defaults to 0 |
| `linestyle` | str or list[str] | — | Closed polygon perimeter style(s) |

## Labels

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | str or list[str] | — | Legend label(s) |

## Scale

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scale` | `"billions"`, `"millions"`, `"thousands"`, `"percentage"` or str | — | Scale formatting for values: divides by scale factor and appends unit label (e.g., 'billions' divides by 1e9 and shows 'B'). Applied to value axis by default. Overrides tick_format specs |
| `axis_scale` | `"x"`, `"y"`, `"both"` | — | Which axis to apply scale formatting to: 'x', 'y', or 'both'. Default: 'y'. For horizontal bars, the value axis is 'x' |

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
