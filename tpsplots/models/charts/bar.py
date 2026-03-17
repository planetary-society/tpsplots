"""Bar chart configuration model.

Covers all kwargs accepted by BarChartView._create_chart / _apply_bar_styling.
"""

from typing import Any, Literal

from pydantic import Field, field_validator

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
    - TickFormatMixin: x_tick_format, y_tick_format, max_xticks, integer_xticks
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

    # --- Rejected fields ---
    @field_validator("fiscal_year_ticks", mode="before")
    @classmethod
    def reject_fiscal_year_ticks(cls, v):
        return cls._reject_fiscal_year_ticks(v, "bar")

    # --- Color parameters ---
    colors: str | list[str] | None = Field(None, description="Bar color(s)")
    positive_color: str | None = Field(
        None, description="Color for positive values (overrides colors)"
    )
    negative_color: str | None = Field(
        None, description="Color for negative values (overrides colors)"
    )
