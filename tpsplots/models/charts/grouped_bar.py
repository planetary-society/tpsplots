"""Grouped bar chart configuration model.

Covers all kwargs accepted by GroupedBarChartView._create_chart.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from tpsplots.models.mixins import (
    AxisMixin,
    BarStylingMixin,
    CategoricalBarAxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ValueAxisVisibilityMixin,
    ValueDisplayMixin,
    ValueScaleMixin,
    validate_bar_value_axis_visibility,
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
    CategoricalBarAxisMixin,
    ValueAxisVisibilityMixin,
    ValueScaleMixin,
    ValueDisplayMixin,
    BarStylingMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: grouped_bar`` charts.

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

    @model_validator(mode="before")
    @classmethod
    def validate_value_axis_visibility(cls, data):
        """Reject horizontal-only x-axis visibility options on grouped bars."""
        return validate_bar_value_axis_visibility(data)
