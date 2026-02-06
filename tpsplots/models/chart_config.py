"""Chart configuration models (v2.0 spec).

The ``ChartConfig`` discriminated union replaces the old ``extra="allow"``
BaseModel.  Pydantic reads the ``type`` field and dispatches to the
corresponding per-chart config model in O(1).
"""

from typing import Annotated, Literal

from pydantic import Discriminator, Tag

from tpsplots.models.charts.bar import BarChartConfig
from tpsplots.models.charts.donut import DonutChartConfig
from tpsplots.models.charts.grouped_bar import GroupedBarChartConfig
from tpsplots.models.charts.line import (
    LineChartConfig,
)
from tpsplots.models.charts.line_subplots import LineSubplotsChartConfig
from tpsplots.models.charts.lollipop import LollipopChartConfig
from tpsplots.models.charts.scatter import ScatterChartConfig
from tpsplots.models.charts.stacked_bar import StackedBarChartConfig
from tpsplots.models.charts.us_map_pie import USMapPieChartConfig
from tpsplots.models.charts.waffle import WaffleChartConfig

# ---------------------------------------------------------------------------
# Chart type mapping: v2.0 name → v1.0 view method name
# ---------------------------------------------------------------------------
CHART_TYPES = {
    "line": "line_plot",
    "scatter": "scatter_plot",
    "bar": "bar_plot",
    "donut": "donut_plot",
    "lollipop": "lollipop_plot",
    "stacked_bar": "stacked_bar_plot",
    "waffle": "waffle_plot",
    "us_map_pie": "us_map_pie_plot",
    "line_subplots": "line_subplots_plot",
    "grouped_bar": "grouped_bar_plot",
}

ChartType = Literal[
    "line",
    "scatter",
    "bar",
    "donut",
    "lollipop",
    "stacked_bar",
    "waffle",
    "us_map_pie",
    "line_subplots",
    "grouped_bar",
]

# ---------------------------------------------------------------------------
# Discriminated union — Pydantic dispatches on the ``type`` field
# ---------------------------------------------------------------------------
ChartConfig = Annotated[
    Annotated[LineChartConfig, Tag("line")]
    | Annotated[ScatterChartConfig, Tag("scatter")]
    | Annotated[BarChartConfig, Tag("bar")]
    | Annotated[DonutChartConfig, Tag("donut")]
    | Annotated[LollipopChartConfig, Tag("lollipop")]
    | Annotated[StackedBarChartConfig, Tag("stacked_bar")]
    | Annotated[WaffleChartConfig, Tag("waffle")]
    | Annotated[GroupedBarChartConfig, Tag("grouped_bar")]
    | Annotated[USMapPieChartConfig, Tag("us_map_pie")]
    | Annotated[LineSubplotsChartConfig, Tag("line_subplots")],
    Discriminator("type"),
]


# ---------------------------------------------------------------------------
# Legacy models — kept for backwards compatibility
# ---------------------------------------------------------------------------
from pydantic import BaseModel, Field  # noqa: E402


class MetadataConfig(BaseModel):
    """Legacy metadata configuration (v1.0 compatibility)."""

    title: str = Field(..., description="Chart title")
    subtitle: str | None = Field(None, description="Chart subtitle")
    source: str | None = Field(None, description="Data source attribution")
    header: bool | None = Field(None, description="Show header section")
    footer: bool | None = Field(None, description="Show footer section")
