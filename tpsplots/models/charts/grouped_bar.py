"""Grouped bar chart configuration model.

Covers all kwargs accepted by GroupedBarChartView._create_chart.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from tpsplots.models.mixins import (
    AxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    TickFormatMixin,
    ValueDisplayMixin,
)


class GroupConfig(BaseModel):
    """Configuration for a single group in a grouped bar chart."""

    label: str | None = Field(None, description="Group label for legend")
    values: list | None = Field(None, description="Values for each category")
    color: str | None = Field(None, description="Primary color for this group")
    stacked_values: list | None = Field(
        None, description="Additional values to stack on last category"
    )
    stacked_color: str | None = Field(None, description="Color for stacked portion")

    model_config = {"extra": "allow"}


class GroupedBarChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ValueDisplayMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: grouped_bar`` charts.

    Inherits shared fields from mixins:
    - AxisMixin: xlim, ylim, xlabel, ylabel, tick_rotation, tick_size, label_size
    - GridMixin: grid, grid_axis
    - LegendMixin: legend
    - TickFormatMixin: x_tick_format, y_tick_format, fiscal_year_ticks, max_xticks
    - ScaleMixin: scale, axis_scale
    - ValueDisplayMixin: show_values, value_format, value_suffix, value_offset,
      value_fontsize, value_color, value_weight
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["grouped_bar"] = Field("grouped_bar", description="Chart type discriminator")

    # --- Data bindings ---
    categories: Any = Field(None, description="Category labels for x-axis")
    groups: list[GroupConfig | dict] | None = Field(
        None, description="List of group configurations"
    )

    # --- Styling ---
    colors: str | list[str] | None = Field(None, description="Override colors for groups")
    labels: str | list[str] | None = Field(
        None, description="Legend labels for each group (overrides group label)"
    )
    width: float | None = Field(
        None,
        description=(
            "Width of each individual bar within a group as fraction of category spacing. "
            "Default: 0.35. Bars are centered around each category position with "
            "total group width = width x num_groups"
        ),
    )
    bar_width: float | None = Field(
        None, description="Width of each bar (legacy alias for width). Default: 0.35"
    )
    alpha: float | None = Field(None, description="Bar transparency (0.0-1.0)")
    edgecolor: str | None = Field(None, description="Bar edge color")
    linewidth: float | None = Field(None, description="Bar edge line width")

    # --- Grouped-bar specific ---
    show_yticks: bool | None = Field(
        None,
        description=(
            "Show y-axis tick labels and left spine. Default: False (y-axis hidden). "
            "When False, the left spine is also removed for a cleaner look. "
            "When True, scale formatting is applied to the y-axis"
        ),
    )
    value_prefix: str | None = Field(
        None,
        description=(
            "Text prepended before each formatted value label. Default: '' (empty). "
            "Examples: '$', '~'. Combined with value_suffix for full formatting"
        ),
    )

    # --- Legacy tick format aliases ---
    x_axis_format: str | None = Field(
        None, description="X-axis tick format (legacy alias for x_tick_format)"
    )
    y_axis_format: str | None = Field(
        None, description="Y-axis tick format (legacy alias for y_tick_format)"
    )
