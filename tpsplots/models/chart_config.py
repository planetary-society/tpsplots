"""Chart configuration models (v2.0 spec)."""

from typing import Literal

from pydantic import BaseModel, Field

# Chart type mapping: v2.0 name → v1.0 view method name
CHART_TYPES = {
    "line": "line_plot",
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
    "bar",
    "donut",
    "lollipop",
    "stacked_bar",
    "waffle",
    "us_map_pie",
    "line_subplots",
    "grouped_bar",
]


class DirectLineLabelsConfig(BaseModel):
    """Configuration for direct line labels."""

    fontsize: int | None = Field(None, description="Font size for labels")
    position: Literal["right", "left", "auto"] | None = Field("auto", description="Label position")
    bbox: bool | None = Field(True, description="Add background box to labels")


class SeriesConfig(BaseModel):
    """Configuration for a single data series."""

    y: str = Field(..., description="Y-axis data reference")
    color: str | None = Field(None, description="Series color")
    linestyle: str | None = Field(None, description="Line style")
    linewidth: float | None = Field(None, description="Line width")
    marker: str | None = Field(None, description="Marker style")
    label: str | None = Field(None, description="Series label")


class ChartConfig(BaseModel):
    """Complete chart configuration (v2.0 spec).

    This model represents everything under the `chart:` section,
    including type, output, metadata, and all chart parameters.
    """

    # Required fields
    type: ChartType = Field(..., description="Chart type")
    output: str = Field(..., description="Base filename for chart outputs")
    title: str = Field(..., description="Chart title")

    # Optional metadata
    subtitle: str | None = Field(
        None, description="Chart subtitle (supports {{variable}} templates)"
    )
    source: str | None = Field(None, description="Data source attribution")

    # Allow any additional parameters for chart-specific options
    model_config = {"extra": "allow"}

    def get_view_method_name(self) -> str:
        """Get the view method name for this chart type."""
        return CHART_TYPES.get(self.type, f"{self.type}_plot")


# Legacy model for backwards compatibility
class MetadataConfig(BaseModel):
    """Legacy metadata configuration (v1.0 compatibility)."""

    title: str = Field(..., description="Chart title")
    subtitle: str | None = Field(None, description="Chart subtitle")
    source: str | None = Field(None, description="Data source attribution")
    header: bool | None = Field(None, description="Show header section")
    footer: bool | None = Field(None, description="Show footer section")
