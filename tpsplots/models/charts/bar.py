"""Bar chart configuration model.

Covers all kwargs accepted by BarChartView._create_chart / _apply_bar_styling.
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
    SortMixin,
    TickFormatMixin,
    ValueDisplayMixin,
)


class BarChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ValueDisplayMixin,
    BarStylingMixin,
    SortMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: bar`` charts.

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
    - SortMixin: sort_by, sort_ascending
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["bar"] = Field("bar", description="Chart type discriminator")

    # --- Data bindings ---
    categories: Any = Field(None, description="Category labels for the axis")
    values: Any = Field(None, description="Bar values")

    # --- Color parameters ---
    colors: str | list[str] | None = Field(None, description="Bar color(s)")
    positive_color: str | None = Field(
        None, description="Color for positive values (overrides colors)"
    )
    negative_color: str | None = Field(
        None, description="Color for negative values (overrides colors)"
    )
