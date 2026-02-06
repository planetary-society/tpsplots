"""Bar-family shared parameter mixin models.

These mixin models define field groups shared across bar-type chart views
(BarChartView, StackedBarChartView, GroupedBarChartView).

IMPORTANT: No mixin class may set ``model_config``. Only ChartConfigBase
sets it. See base.py docstring for rationale.
"""

from typing import Literal

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


class BarStylingMixin(BaseModel):
    """Shared bar styling parameters.

    Used by: bar, stacked_bar.
    Mirrors: BarChartMixin._apply_common_bar_styling
    """

    width: float | None = Field(
        None,
        description=(
            "Bar width as fraction of category spacing (0.0-1.0). Default: 0.8. "
            "Only applies to vertical bars; use height for horizontal. "
            "For grouped bars, controls individual bar width (default: 0.35)"
        ),
    )
    height: float | None = Field(
        None,
        description=(
            "Bar height as fraction of category spacing (0.0-1.0). Default: 0.8. "
            "Only applies to horizontal bars; use width for vertical"
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
    orientation: Literal["vertical", "horizontal"] | None = Field(
        None,
        description=(
            "Bar orientation: 'vertical' (categories on x, values on y) "
            "or 'horizontal' (categories on y, values on x). Default: 'vertical'"
        ),
    )
    show_category_ticks: bool | None = Field(
        None,
        description=(
            "Show tick marks on the category axis (x for vertical, y for horizontal). "
            "Default: False (tick marks hidden, but labels remain visible)"
        ),
    )
    baseline: float | None = Field(
        None,
        description=(
            "Reference value for bar positioning. Default: 0. "
            "When non-zero, draws a gray reference line and positions value labels relative to it"
        ),
    )
