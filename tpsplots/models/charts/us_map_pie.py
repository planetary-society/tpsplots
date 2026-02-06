"""US Map Pie chart configuration model.

Covers all kwargs accepted by USMapPieChartView._create_chart.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import ChartConfigBase


class USMapPieChartConfig(ChartConfigBase):
    """Validated configuration for ``type: us_map_pie`` charts.

    Inherits from ChartConfigBase only (no axis/grid/legend mixins —
    US map pie charts handle their own legend and axes).
    """

    type: Literal["us_map_pie"] = Field("us_map_pie", description="Chart type discriminator")

    # --- Data bindings ---
    pie_data: Any = Field(
        None,
        description=(
            "Dict mapping location names to pie chart data dicts "
            "(each with 'values', 'labels', 'colors')"
        ),
    )

    # --- Pie sizing ---
    pie_size_column: str | None = Field(
        None,
        description=(
            "Key name in each pie_data entry to use for proportional pie sizing. "
            "When set, pie sizes are normalized between min_pie_size and max_pie_size. "
            "When omitted, all pies use base_pie_size"
        ),
    )
    base_pie_size: float | None = Field(
        None,
        description=(
            "Base scatter size for pie charts in points-squared. Default: 800. "
            "Automatically scaled 2x for desktop. Used as uniform size when pie_size_column is omitted"
        ),
    )
    max_pie_size: float | None = Field(
        None,
        description=(
            "Maximum scatter size for proportional pie sizing in points-squared. Default: 1500. "
            "Automatically scaled 2x for desktop. Only applies when pie_size_column is set"
        ),
    )
    min_pie_size: float | None = Field(
        None,
        description=(
            "Minimum scatter size for proportional pie sizing in points-squared. Default: 400. "
            "Automatically scaled 2x for desktop. Only applies when pie_size_column is set"
        ),
    )

    # --- Map configuration ---
    custom_locations: dict[str, Any] | None = Field(
        None, description="Custom location coordinates to override defaults"
    )
    show_state_boundaries: bool | None = Field(
        None,
        description=(
            "Show white state boundary lines on the US map. Default: True. "
            "When False, boundaries blend into the gray background for a cleaner look"
        ),
    )

    # --- Display options ---
    show_pie_labels: bool | None = Field(None, description="Show labels on pie charts")
    show_percentages: bool | list[bool] | None = Field(
        None, description="Show percentage values on pie segments"
    )
    legend_location: str | None = Field(
        None, description="Location for legend (currently unused by view)"
    )
    pie_edge_color: str | None = Field(
        None, description="Edge color for pie charts (currently unused by view)"
    )
    pie_edge_width: float | None = Field(
        None, description="Edge width for pie charts (currently unused by view)"
    )

    # --- Offset line styling ---
    offset_line_color: str | None = Field(
        None, description="Color for connecting lines from offset pies"
    )
    offset_line_style: str | None = Field(None, description="Style for connecting lines")
    offset_line_width: float | None = Field(None, description="Width for connecting lines")

    # --- Layout ---
    auto_expand_bounds: bool | None = Field(
        None, description="Automatically expand figure bounds to fit all pies"
    )
    padding_factor: float | None = Field(
        None,
        description=(
            "Extra padding around pies when auto-expanding bounds, as fraction of pie radius. "
            "Default: 0 for desktop, 0.15 for mobile. "
            "Increase to prevent pies from being clipped at figure edges"
        ),
    )
