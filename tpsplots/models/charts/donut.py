"""Donut chart configuration model.

Covers all kwargs accepted by DonutChartView._create_chart.
After popping known fields, remaining kwargs pass through to ax.pie() —
use the inherited ``matplotlib_config`` escape hatch for less common
pie() parameters like ``pctdistance``, ``shadow``, ``normalize``, etc.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import ChartConfigBase


class DonutChartConfig(ChartConfigBase):
    """Validated configuration for ``type: donut`` charts.

    Inherits from ChartConfigBase only (no axis/grid/legend mixins —
    donut charts turn off axes entirely).

    Use ``matplotlib_config`` for any kwargs that should pass through
    to matplotlib's ``ax.pie()`` call.
    """

    type: Literal["donut"] = Field("donut", description="Chart type discriminator")

    # --- Data bindings ---
    values: Any = Field(None, description="Values for each donut segment")
    labels: Any = Field(None, description="Labels for each segment")

    # --- Styling ---
    colors: list[str] | None = Field(None, description="Colors for each segment")
    hole_size: float | None = Field(
        None,
        description=(
            "Relative size of donut hole as fraction of pie radius (0.0-1.0). "
            "Default: 0.7. Set to 0 for a solid pie chart, 1.0 for a thin ring"
        ),
    )
    center_text: str | None = Field(
        None,
        description=(
            "Text displayed in the center of the donut hole. "
            "Rendered at title_size with bold weight. Typically used for totals or key metrics"
        ),
    )
    center_color: str | None = Field(
        None,
        description=(
            "Fill color of the center circle (donut hole). "
            "Default: light_gray (#D3D3D3). Accepts any matplotlib color or TPS brand name"
        ),
    )
    show_percentages: bool | None = Field(
        None,
        description=(
            "Show percentage values alongside each segment label (e.g., 'Science\\n(25.0%)'). "
            "Default: True. Percentages are auto-calculated from values"
        ),
    )
    label_wrap_length: int | None = Field(
        None,
        description=(
            "Maximum characters per line for segment labels before word-wrapping. "
            "Default: from style (typically 15). Labels wrap on word boundaries"
        ),
    )
    label_distance: float | None = Field(
        None,
        description=(
            "Distance of segment labels from chart center in plot units. "
            "Default: 1.4 (placed outside the pie radius). "
            "Increase to push labels further out if they overlap segments"
        ),
    )
    wedgeprops: dict[str, Any] | None = Field(
        None, description="Properties for pie wedges (linewidth, edgecolor, etc.)"
    )
