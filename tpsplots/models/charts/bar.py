"""Bar chart configuration model.

Covers all kwargs accepted by BarChartView._create_chart / _apply_bar_styling.
"""

from typing import Any, Literal

from pydantic import Field, model_validator

from tpsplots.models.mixins import (
    AxisMixin,
    BarStylingMixin,
    CategoricalBarAxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    SortMixin,
    ValueAxisVisibilityMixin,
    ValueDisplayMixin,
    ValueScaleMixin,
    validate_bar_value_axis_visibility,
)


class BarChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    CategoricalBarAxisMixin,
    ValueAxisVisibilityMixin,
    ValueScaleMixin,
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
    - CategoricalBarAxisMixin: x_tick_format, y_tick_format, category_label_format
    - ValueAxisVisibilityMixin: show_xticks, show_yticks
    - ValueScaleMixin: scale
    - ValueDisplayMixin: show_values, value_prefix, value_format, value_suffix,
      value_offset, value_fontsize, value_color, value_weight
    - BarStylingMixin: width, alpha, edgecolor, linewidth, show_category_ticks
    - SortMixin: sort_by, sort_ascending
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["bar"] = Field("bar", description="Chart type discriminator")

    # --- Data bindings ---
    categories: Any = Field(None, description="Category labels for the axis")
    values: Any = Field(None, description="Bar values")

    # --- Orientation (bar + stacked_bar only) ---
    height: float | None = Field(
        None,
        description=(
            "Bar height as fraction of category spacing (0.0-1.0). Default: 0.8. "
            "Only applies to horizontal bars; use width for vertical"
        ),
    )
    orientation: Literal["vertical", "horizontal"] | None = Field(
        None,
        description=(
            "Bar orientation: 'vertical' (categories on x, values on y) "
            "or 'horizontal' (categories on y, values on x). Default: 'vertical'"
        ),
    )
    baseline: float | None = Field(
        None,
        description=(
            "Reference value for bar positioning. Default: 0. "
            "When non-zero, draws a gray reference line and positions value labels relative to it"
        ),
    )

    # --- Color parameters ---
    colors: str | list[str] | None = Field(None, description="Bar color(s)")
    positive_color: str | None = Field(
        None, description="Color for positive values (overrides colors)"
    )
    negative_color: str | None = Field(
        None, description="Color for negative values (overrides colors)"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_value_axis_visibility(cls, data):
        """Reject x/y value-axis visibility options on incompatible orientations."""
        return validate_bar_value_axis_visibility(data)
