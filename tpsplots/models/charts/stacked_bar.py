"""Stacked bar chart configuration model.

Covers all kwargs accepted by StackedBarChartView._create_chart /
_apply_stacked_bar_styling.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import (
    AxisMixin,
    BarStylingMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    TickFormatMixin,
    ValueDisplayMixin,
)


class StackedBarChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ValueDisplayMixin,
    BarStylingMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: stacked_bar`` charts.

    Inherits shared fields from mixins:
    - AxisMixin: xlim, ylim, xlabel, ylabel, tick_rotation, tick_size, label_size
    - GridMixin: grid, grid_axis
    - LegendMixin: legend
    - TickFormatMixin: x_tick_format, y_tick_format, fiscal_year_ticks, max_xticks
    - ScaleMixin: scale, axis_scale
    - ValueDisplayMixin: show_values, value_format, value_suffix, value_offset,
      value_fontsize, value_color, value_weight
    - BarStylingMixin: width, height, alpha, edgecolor, linewidth, orientation,
      show_category_ticks, baseline
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["stacked_bar"] = Field("stacked_bar", description="Chart type discriminator")

    # --- Data bindings ---
    categories: Any = Field(None, description="Category labels for the axis")
    values: Any = Field(
        None,
        description="Stack segment values (dict or DataFrame)",
    )
    labels: list[str] | str | None = Field(
        None, description="Labels for each stack segment or template ref"
    )

    # --- Styling ---
    colors: list[str] | str | None = Field(
        None, description="Colors for each stack segment or template ref"
    )

    # --- Stacked-bar specific ---
    value_threshold: float | None = Field(
        None,
        description=(
            "Minimum segment size as percentage of bar total to display a value label. "
            "Default: 5.0 (segments <5% of total are unlabeled). "
            "Set to 0 to label all non-zero segments"
        ),
    )
    stack_labels: bool | None = Field(
        None,
        description=(
            "Show total value labels at the end of each stacked bar (above for vertical, "
            "right for horizontal). Default: False. Rendered in bold dark_gray at value_fontsize"
        ),
    )
    stack_label_format: str | None = Field(
        None,
        description=(
            "Format for stack total labels: preset ('monetary', 'percentage', 'integer', 'float') "
            "or Python format spec. Default: same as value_format"
        ),
    )
    stack_label_suffix: str | None = Field(
        None,
        description=(
            "Text appended after each stack total label. "
            "Default: same as value_suffix. Examples: ' B', ' M'"
        ),
    )
    bottom_values: list | None = Field(
        None, description="Custom bottom values for stacking (advanced use)"
    )
