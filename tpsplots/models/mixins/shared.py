"""Shared parameter group mixin models for chart configurations.

These mixin models define field groups that are shared across multiple chart
types. They mirror the view-layer mixins (GridAxisMixin, AxisTickFormatMixin,
etc.) but exist at the validation/schema layer.

IMPORTANT: No mixin class may set ``model_config``. Only ChartConfigBase
sets it. See base.py docstring for rationale.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from tpsplots.models.mixins.base import validate_numeric_or_ref

NumericFloatOrRef = Annotated[float | str, BeforeValidator(validate_numeric_or_ref)]
NumericIntOrRef = Annotated[int | str, BeforeValidator(validate_numeric_or_ref)]


class AxisMixin(BaseModel):
    """Shared axis configuration parameters.

    Used by: line, scatter, bar, stacked_bar, grouped_bar, lollipop, line_subplots.
    Mirrors: GridAxisMixin._apply_axis_labels, _apply_axis_limits
    """

    # NOTE: xlim/ylim accept dates because YAML parses "2006-01-01" as
    # datetime.date objects. Real YAML files use e.g. xlim: [1958-01-01, 2030-01-01].
    xlim: list | dict | str | None = Field(
        None, description="X-axis limits as [min, max], {left: val, right: val}, or template ref"
    )
    ylim: list | dict | str | None = Field(
        None, description="Y-axis limits as [min, max], {bottom: val, top: val}, or template ref"
    )
    xlabel: str | None = Field(None, description="X-axis label text")
    ylabel: str | None = Field(None, description="Y-axis label text")
    tick_rotation: float | None = Field(
        None,
        description=(
            "Rotation angle in degrees for x-axis tick labels. "
            "Default: 45 for vertical bars, 0 for horizontal bars and line charts. "
            "Scaled to 80% on mobile"
        ),
    )
    tick_size: NumericFloatOrRef | None = Field(
        None,
        description=(
            "Font size in points for axis tick labels. "
            "Default: from style (typically 12pt). Scaled to 80% on mobile. "
            "Applied to both x and y axes"
        ),
    )
    label_size: NumericFloatOrRef | None = Field(
        None,
        description=(
            "Font size in points for axis labels (xlabel/ylabel). "
            "Default: from style (typically 20pt). Scaled to 60% on mobile. "
            "Does not affect tick label size"
        ),
    )


class GridMixin(BaseModel):
    """Shared grid configuration parameters.

    Used by: line, scatter, bar, stacked_bar, grouped_bar, lollipop, line_subplots.
    Mirrors: GridAxisMixin._apply_grid
    """

    grid: bool | dict | str | None = Field(
        None,
        description=(
            "Grid display: True/False for default grid, or dict of ax.grid() kwargs "
            "(e.g., {alpha: 0.3, linestyle: '--'}). Default depends on chart type"
        ),
    )
    grid_axis: Literal["x", "y", "both"] | None = Field(
        None,
        description=(
            "Which axis to show grid lines on: 'x', 'y', or 'both'. "
            "Default: 'y' for vertical charts, 'x' for horizontal charts"
        ),
    )


class LegendMixin(BaseModel):
    """Shared legend configuration parameters.

    Used by: line, scatter, bar, stacked_bar, grouped_bar, waffle, line_subplots.
    """

    legend: bool | dict | str | None = Field(
        None,
        description=(
            "Legend display: False to hide, True for default, "
            "or dict of ax.legend() kwargs (e.g., {loc: 'upper right', fontsize: 'medium', ncol: 3})"
        ),
    )


class TickFormatMixin(BaseModel):
    """Shared tick format configuration parameters.

    Used by: line, scatter, bar, stacked_bar, grouped_bar, lollipop, line_subplots.
    Mirrors: AxisTickFormatMixin._apply_tick_format_specs
    """

    x_tick_format: str | None = Field(
        None,
        description=(
            "Python format spec for x-axis tick labels (e.g., '.0f', ',.0f'). "
            "Applied via FuncFormatter. Ignored if scale formatting is active"
        ),
    )
    y_tick_format: str | None = Field(
        None,
        description=(
            "Python format spec for y-axis tick labels (e.g., '.0f', ',.0f'). "
            "Applied via FuncFormatter. Ignored if scale formatting is active"
        ),
    )
    fiscal_year_ticks: bool | None = Field(
        None,
        description=(
            "Format x-axis ticks as fiscal years using date formatting. "
            "Default: True if x-axis data contains dates. Auto-adjusts density: "
            "all years if <10yr range, every 5yr if <20yr, decades if >20yr"
        ),
    )
    max_xticks: NumericIntOrRef | None = Field(
        None,
        description=(
            "Maximum number of x-axis ticks. For numeric axes, uses MaxNLocator. "
            "For categorical axes, calculates step = len(categories) // max_xticks + 1"
        ),
    )


class ScaleMixin(BaseModel):
    """Shared scale configuration parameters.

    Used by: line, scatter, bar, stacked_bar, grouped_bar, lollipop, line_subplots.
    Mirrors: ChartView._apply_scale_formatter
    """

    scale: Literal["billions", "millions", "thousands", "percentage"] | str | None = Field(
        None,
        description=(
            "Scale formatting for values: divides by scale factor and appends unit label "
            "(e.g., 'billions' divides by 1e9 and shows 'B'). "
            "Applied to value axis by default. Overrides tick_format specs"
        ),
    )
    axis_scale: Literal["x", "y", "both"] | None = Field(
        None,
        description=(
            "Which axis to apply scale formatting to: 'x', 'y', or 'both'. "
            "Default: 'y'. For horizontal bars, the value axis is 'x'"
        ),
    )


class SortMixin(BaseModel):
    """Shared sorting configuration parameters.

    Used by: bar, lollipop, stacked_bar (via sort_by patterns).
    """

    sort_by: str | None = Field(
        None,
        description=(
            "Sort criterion (chart-specific). Bar: 'value' or 'category'. "
            "Lollipop: 'start', 'end', or 'range'. Stacked bar: 'total' or 'category'"
        ),
    )
    sort_ascending: bool | None = Field(
        None,
        description="Sort direction. Default: False (descending, largest first)",
    )
