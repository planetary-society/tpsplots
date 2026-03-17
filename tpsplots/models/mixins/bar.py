"""Bar-family shared parameter mixin models.

These mixin models define field groups shared across bar-type chart views
(BarChartView, StackedBarChartView, GroupedBarChartView).

IMPORTANT: No mixin class may set ``model_config``. Only ChartConfigBase
sets it. See base.py docstring for rationale.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ValueDisplayMixin(BaseModel):
    """Shared value label display parameters for bar-type charts.

    Used by: bar, stacked_bar, grouped_bar.
    Mirrors: BarChartMixin._add_bar_value_labels
    """

    show_values: bool | None = Field(
        None,
        description=(
            "Display formatted value labels on each bar. "
            "Positioned above positive bars / below negative bars (vertical), "
            "or right/left (horizontal). Configure with value_format, value_suffix, etc."
        ),
    )
    value_format: str | None = Field(
        None,
        description=(
            "Format for value labels: preset name or Python format spec. "
            "Presets: 'monetary' -> ',.0f', 'percentage' -> '.1f%' (also formats axis ticks), "
            "'integer' -> '.0f', 'float' -> '.2f'. Or direct spec like ',.0f'"
        ),
    )
    value_prefix: str | None = Field(
        None,
        description=(
            "Text prepended before each formatted value label. Default: '' (empty). "
            "Examples: '$', '~'. Combined with value_suffix for full formatting"
        ),
    )
    value_suffix: str | None = Field(
        None,
        description=(
            "Text appended after each formatted value label. "
            "Examples: ' yrs', ' months', ' B' for billions. Default: empty string"
        ),
    )
    value_offset: float | None = Field(
        None,
        description=(
            "Distance from bar end to value label in data units. "
            "Default: None (auto-calculates as 2% of value axis range). "
            "Negative values place labels inside the bar"
        ),
    )
    value_fontsize: float | str | None = Field(
        None,
        description=(
            "Font size in points for value labels. "
            "Default: 0.9x tick_size for bars, 0.8x for stacked/grouped bars"
        ),
    )
    value_color: str | None = Field(
        None,
        description=(
            "Text color for value labels. "
            "Default: 'black' for regular bars, 'white' for stacked bars (contrast on colored segments)"
        ),
    )
    value_weight: Literal["normal", "bold"] | str | None = Field(
        None,
        description=(
            "Font weight for value labels: 'normal' or 'bold'. "
            "Default: 'bold' for stacked bars, 'normal' for regular/grouped bars"
        ),
    )


class CategoricalBarAxisMixin(BaseModel):
    """Axis/tick parameters shared by categorical bar-family charts.

    Used by: bar, grouped_bar, stacked_bar.
    """

    x_tick_format: str | None = Field(
        None,
        description=(
            "Python format spec for x-axis tick labels on numeric value axes "
            "or horizontal bar value axes. Ignored if scale formatting is active"
        ),
    )
    y_tick_format: str | None = Field(
        None,
        description=(
            "Python format spec for y-axis tick labels on numeric value axes "
            "or vertical bar value axes. Ignored if scale formatting is active"
        ),
    )
    category_label_format: str | None = Field(
        None,
        description=(
            "Formatting for category labels when categories are date-like. "
            "Use 'year' to render YYYY, or any strftime format such as '%Y-%m'. "
            "Default: auto-detect year-like dates and render readable labels"
        ),
    )


class ValueAxisVisibilityMixin(BaseModel):
    """Value-axis visibility controls shared by categorical bar-family charts."""

    show_xticks: bool | None = Field(
        None,
        description=(
            "Show x-axis tick labels and bottom spine on horizontal bar charts. "
            "Default: True for horizontal charts. Not supported for vertical charts"
        ),
    )
    show_yticks: bool | None = Field(
        None,
        description=(
            "Show y-axis tick labels and left spine on vertical bar charts. "
            "Default: True for vertical charts. Not supported for horizontal charts"
        ),
    )


def validate_bar_value_axis_visibility(data: Any, *, default_orientation: str = "vertical") -> Any:
    """Validate show_xticks/show_yticks against the chart orientation."""
    if not isinstance(data, dict):
        return data

    orientation = data.get("orientation", default_orientation) or default_orientation

    if orientation == "vertical" and data.get("show_xticks") is not None:
        raise ValueError("show_xticks is only supported for horizontal bar charts")

    if orientation == "horizontal" and data.get("show_yticks") is not None:
        raise ValueError("show_yticks is only supported for vertical bar charts")

    return data


class ValueScaleMixin(BaseModel):
    """Scale configuration for chart value axes.

    Used by: bar, grouped_bar, stacked_bar.
    """

    scale: Literal["billions", "millions", "thousands", "percentage"] | str | None = Field(
        None,
        description=(
            "Scale formatting for the chart value axis: divides by scale factor and "
            "appends unit labels (for example 'billions' -> 'B'). "
            "Overrides tick_format specs on the value axis"
        ),
    )


class BarStylingMixin(BaseModel):
    """Shared bar styling parameters.

    Used by: bar, grouped_bar, stacked_bar.
    """

    width: float | None = Field(
        None,
        description=(
            "Bar width as fraction of category spacing (0.0-1.0). Default: 0.8. "
            "Only applies to vertical bars; use height for horizontal. "
            "For grouped bars, controls individual bar width (default: 0.35)"
        ),
    )
    alpha: float | None = Field(
        None,
        description="Bar transparency (0.0 = fully transparent, 1.0 = fully opaque). Default: 1.0",
    )
    edgecolor: str | None = Field(
        None,
        description=(
            "Bar border color. Default: 'white'. "
            "Works with linewidth to create visible borders between adjacent bars"
        ),
    )
    linewidth: float | None = Field(
        None,
        description="Bar border line width in points. Default: 0.5. Set to 0 to remove borders",
    )
    show_category_ticks: bool | None = Field(
        None,
        description=(
            "Show tick marks on the category axis (x for vertical, y for horizontal). "
            "Default: False (tick marks hidden, but labels remain visible)"
        ),
    )
