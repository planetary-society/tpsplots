# Bar Family Behavior Matrix

This document records the canonical bar-family contract after the categorical-bar
consistency refactor.

## Shared Defaults

| Behavior                                       | `bar` | `grouped_bar` | `stacked_bar` |
| ---------------------------------------------- | ----- | ------------- | ------------- |
| Visible y-axis by default                      | Yes   | Yes           | Yes           |
| Italic axis labels                             | Yes   | Yes           | Yes           |
| Category tick marks hidden by default          | Yes   | Yes           | Yes           |
| Readable date-like category labels by default  | Yes   | Yes           | Yes           |
| Shared value-axis scale / tick-format pipeline | Yes   | Yes           | Yes           |

## Intentional Differences

| Behavior                                | `bar`   | `grouped_bar` | `stacked_bar` |
| --------------------------------------- | ------- | ------------- | ------------- |
| Default `legend`                        | `False` | `True`        | `True`        |
| Baseline / sign-color logic             | Yes     | No            | No            |
| Partial stacked-tail rendering          | No      | Yes           | No            |
| Segment-threshold labels / stack totals | No      | No            | Yes           |

## Shared Bar Styling Surface

All three bar types inherit `BarStylingMixin` with these fields:

- `width` — bar width (default: 0.8 for bar/stacked, 0.35 for grouped)
- `alpha`
- `edgecolor`
- `linewidth`
- `show_category_ticks`

Additionally, `bar` and `stacked_bar` support `height`, `orientation`, and
`bar` supports `baseline` (not applicable to grouped or stacked).

## Shared Value Label Surface

All three bar types inherit `ValueDisplayMixin` with these fields:

- `show_values`
- `value_prefix`
- `value_format`
- `value_suffix`
- `value_offset`
- `value_fontsize`
- `value_color`
- `value_weight`

Additionally, `stacked_bar` has `stack_label_prefix`, `stack_label_format`,
`stack_label_suffix`, and `stack_labels` for stack total labels.

## Supported Categorical Axis Surface

The bar family shares these category/value-axis options:

- `x_tick_format`
- `y_tick_format`
- `category_label_format`
- `scale`
- `tick_rotation`
- `tick_size`
- `label_size`
- `show_category_ticks`
- `show_xticks`
- `show_yticks`
- `grid`
- `grid_axis`
- `xlim`
- `ylim`

## Intentionally Unsupported Shared Fields

The following fields are not part of the bar-family contract:

- `axis_scale`
- `max_xticks`
- `fiscal_year_ticks`

These remain line/scatter-style axis concepts and are intentionally not exposed
for categorical bar charts.

## Date-Like Category Labels

Bar-family charts do not convert categorical axes into continuous date axes.

- Date-like category values render as readable labels.
- Year-boundary timestamps such as `1959-01-01` auto-render as `1959`.
- `category_label_format: "year"` forces `YYYY`.
- `category_label_format: "%Y-%m"` and other `strftime` patterns are supported.
- `xlim` and `ylim` remain positional/value-axis controls, not date-range controls.
- `show_yticks` is only valid for vertical bars, and `show_xticks` is only valid for horizontal bars.
