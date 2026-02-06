"""Lollipop chart configuration model.

Covers all kwargs accepted by LollipopChartView._create_chart /
_format_lollipop_chart / _apply_lollipop_styling.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import (
    AxisMixin,
    ChartConfigBase,
    GridMixin,
    ScaleMixin,
    SortMixin,
    TickFormatMixin,
)


class LollipopChartConfig(
    AxisMixin,
    GridMixin,
    TickFormatMixin,
    ScaleMixin,
    SortMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: lollipop`` charts.

    Inherits shared fields from mixins:
    - AxisMixin: xlim, ylim, xlabel, ylabel, tick_rotation, tick_size, label_size
    - GridMixin: grid, grid_axis
    - TickFormatMixin: x_tick_format, y_tick_format, fiscal_year_ticks, max_xticks
    - ScaleMixin: scale, axis_scale
    - SortMixin: sort_by, sort_ascending
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["lollipop"] = Field("lollipop", description="Chart type discriminator")

    # --- Data bindings ---
    categories: Any = Field(None, description="Category labels for y-axis")
    start_values: Any = Field(None, description="Start values for each range (left side)")
    end_values: Any = Field(None, description="End values for each range (right side)")

    # --- Styling ---
    colors: str | list[str] | None = Field(None, description="Lollipop color(s)")
    marker_size: int | float | None = Field(None, description="Size of circle markers")
    line_width: float | None = Field(None, description="Width of stem lines")
    marker_style: str | None = Field(
        None,
        description=(
            "Matplotlib marker style for both endpoints. Default: 'o' (circle). "
            "Common values: 's' (square), '^' (triangle), 'D' (diamond). "
            "Override per-endpoint with start_marker_style / end_marker_style"
        ),
    )
    linestyle: str | list[str] | None = Field(None, description="Line style for stems")
    line_style: str | list[str] | None = Field(
        None, description="Line style for stems (alias for linestyle)"
    )
    alpha: float | None = Field(None, description="Transparency (0.0-1.0)")

    # --- Per-endpoint marker customization ---
    start_marker_style: str | None = Field(None, description="Marker style for start points")
    end_marker_style: str | None = Field(None, description="Marker style for end points")
    start_marker_size: int | float | None = Field(None, description="Size for start markers")
    end_marker_size: int | float | None = Field(None, description="Size for end markers")
    start_marker_color: str | list[str] | None = Field(
        None, description="Color(s) for start markers"
    )
    end_marker_color: str | list[str] | None = Field(None, description="Color(s) for end markers")
    start_marker_edgecolor: str | list[str] | None = Field(
        None, description="Edge color(s) for start markers"
    )
    end_marker_edgecolor: str | list[str] | None = Field(
        None, description="Edge color(s) for end markers"
    )
    start_marker_edgewidth: float | None = Field(
        None,
        description="Edge line width in points for start endpoint markers. Default: 1",
    )
    end_marker_edgewidth: float | None = Field(
        None,
        description="Edge line width in points for end endpoint markers. Default: 1",
    )

    # --- Value labels ---
    value_labels: bool | None = Field(None, description="Show value labels at end of ranges")
    range_labels: bool | None = Field(None, description="Show range duration labels")
    start_value_labels: bool | None = Field(None, description="Show start values on left side")
    end_value_labels: bool | None = Field(None, description="Show end values on right side")
    value_format: str | None = Field(
        None,
        description=(
            "Format for value labels: preset ('monetary', 'percentage', 'integer', 'float') "
            "or Python format spec"
        ),
    )
    value_suffix: str | None = Field(None, description="Text to append to formatted values")
    range_format: str | None = Field(
        None, description="Format for range duration labels (defaults to value_format)"
    )
    range_suffix: str | None = Field(
        None, description="Text to append to range labels (defaults to value_suffix)"
    )

    # --- Category and axis customization ---
    category_wrap_length: int | None = Field(
        None,
        description=(
            "Maximum characters per line for category labels before word-wrapping. "
            "Default: from style (typically 20). Labels wrap on word boundaries"
        ),
    )
    y_axis_position: Literal["left", "right"] | None = Field(
        None,
        description=(
            "Position of the y-axis (category labels). Default: 'left'. "
            "Set to 'right' to move category labels to the right side of the chart"
        ),
    )
    y_tick_marker: str | None = Field(
        None,
        description=(
            "Custom character/symbol displayed at each y-axis tick position in place of "
            "standard tick marks. Examples: 'X', '|', '\u2022' (bullet). Default: None (standard ticks). "
            "Rendered in bold at tick_size"
        ),
    )
    y_tick_color: str | None = Field(
        None,
        description=(
            "Color for custom y-axis tick markers (only applies when y_tick_marker is set). "
            "Default: dark_gray. Accepts any matplotlib color or TPS brand name"
        ),
    )
    hide_y_spine: bool | None = Field(
        None,
        description=(
            "Hide the vertical y-axis spine line while keeping tick labels visible. "
            "Default: False (spine shown at 30% opacity). "
            "Set to True for a cleaner floating-label look"
        ),
    )

    # --- Legacy tick format aliases ---
    x_axis_format: str | None = Field(
        None, description="X-axis tick format (legacy alias for x_tick_format)"
    )
    y_axis_format: str | None = Field(
        None, description="Y-axis tick format (legacy alias for y_tick_format)"
    )
