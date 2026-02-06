"""Line subplots configuration model.

Covers all kwargs accepted by LineSubplotsView._create_chart /
_apply_subplot_styling.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import (
    AxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    TickFormatMixin,
)


class LineSubplotsChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: line_subplots`` charts.

    Inherits shared fields from mixins:
    - AxisMixin: xlim, ylim, xlabel, ylabel, tick_rotation, tick_size, label_size
    - GridMixin: grid, grid_axis
    - LegendMixin: legend
    - TickFormatMixin: x_tick_format, y_tick_format, fiscal_year_ticks, max_xticks
    - ScaleMixin: scale, axis_scale
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["line_subplots"] = Field("line_subplots", description="Chart type discriminator")

    # --- Data bindings ---
    subplot_data: Any = Field(
        None,
        description=(
            "List of dicts, each containing x, y, title, labels, colors, "
            "linestyles, markers for one subplot"
        ),
    )

    # --- Grid layout ---
    grid_shape: list[int] | tuple[int, int] | None = Field(
        None,
        description=(
            "Subplot grid as [rows, cols]. Default: auto-calculated from ceil(sqrt(n_plots)). "
            "Unused cells are hidden. Example: [2, 3] for a 2-row x 3-column grid"
        ),
    )

    # --- Subplot behavior ---
    shared_x: bool | None = Field(
        None,
        description=(
            "Share x-axis scale and ticks across all subplots in the same column. "
            "Default: True. When True, only the bottom row shows x-axis tick labels"
        ),
    )
    shared_y: bool | None = Field(
        None,
        description=(
            "Share y-axis scale and ticks across all subplots in the same row. "
            "Default: True. When True, only the leftmost column shows y-axis tick labels"
        ),
    )
    shared_legend: bool | None = Field(
        None,
        description=(
            "Use a single shared legend below the subplot grid instead of per-subplot legends. "
            "Default: False. Labels are collected from the first subplot only (avoids duplicates)"
        ),
    )
    legend_position: list[float] | tuple[float, float] | None = Field(
        None,
        description=(
            "Position for shared legend as [x, y] in figure coordinates (0-1). "
            "Default: [0.5, -0.05] (centered below the grid). "
            "Only applies when shared_legend is True"
        ),
    )
    subplot_title_size: float | None = Field(
        None,
        description=(
            "Font size in points for individual subplot titles. "
            "Default: style label_size (typically 20pt). "
            "Set smaller for dense grids to avoid overlap"
        ),
    )

    # --- Legacy tick format aliases ---
    x_axis_format: str | None = Field(
        None, description="X-axis tick format (legacy alias for x_tick_format)"
    )
    y_axis_format: str | None = Field(
        None, description="Y-axis tick format (legacy alias for y_tick_format)"
    )

    # --- Custom ticks (passed through to subplots) ---
    xticks: list | None = Field(None, description="Custom x-axis tick positions")
    xticklabels: list[str] | None = Field(None, description="Custom x-axis tick labels")
