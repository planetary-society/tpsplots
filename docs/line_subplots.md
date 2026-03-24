# Line Subplots Chart

> Auto-generated from Pydantic models. Do not edit manually.
> Regenerate with: `tpsplots docs`

See also: [Data Configuration](data.md) | [All Chart Types](index.md)

Validated configuration for ``type: line_subplots`` charts.

## Example

```yaml
data:
  source: data/divisions.csv

chart:
  type: line_subplots
  output: science_divisions
  title: "Science Division Budgets"
  subplot_data:
    - x: "{{Fiscal Year}}"
      y: "{{Astrophysics}}"
      title: "Astrophysics"
      color: NeptuneBlue
    - x: "{{Fiscal Year}}"
      y: "{{Planetary}}"
      title: "Planetary Science"
      color: RocketFlame
```

## Data Bindings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `subplot_data` | any (template ref) | — | List of dicts, each containing x, y, title, labels, colors, linestyles, markers for one subplot |

## Subplot Layout

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `grid_shape` | list[int] or tuple[int, int] | — | Subplot grid as [rows, cols]. Default: auto-calculated from ceil(sqrt(n_plots)). Unused cells are hidden. Example: [2, 3] for a 2-row x 3-column grid |
| `shared_x` | bool | — | Share x-axis scale and ticks across all subplots in the same column. Default: True. When True, only the bottom row shows x-axis tick labels |
| `shared_y` | bool | — | Share y-axis scale and ticks across all subplots in the same row. Default: True. When True, only the leftmost column shows y-axis tick labels |
| `shared_legend` | bool | — | Use a single shared legend below the subplot grid instead of per-subplot legends. Default: False. Labels are collected from the first subplot only (avoids duplicates) |
| `legend_position` | list[float] or tuple[float, float] | — | Position for shared legend as [x, y] in figure coordinates (0-1). Default: [0.5, -0.05] (centered below the grid). Only applies when shared_legend is True |
| `subplot_title_size` | float | — | Font size in points for individual subplot titles. Default: style label_size (typically 20pt). Set smaller for dense grids to avoid overlap |

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
