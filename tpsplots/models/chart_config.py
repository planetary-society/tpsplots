"""Chart and metadata configuration models."""

from typing import Literal

from pydantic import BaseModel, Field


class ChartConfig(BaseModel):
    """Chart configuration section."""

    type: Literal[
        "line_plot",
        "bar_plot",
        "donut_plot",
        "lollipop_plot",
        "stacked_bar_plot",
        "waffle_plot",
        "us_map_pie_plot",
        "line_subplots_plot",
    ] = Field(..., description="Chart type matching view method names")
    output_name: str = Field(..., description="Base filename for chart outputs")


class MetadataConfig(BaseModel):
    """Chart metadata configuration."""

    title: str = Field(..., description="Chart title")
    subtitle: str | None = Field(None, description="Chart subtitle (supports templates)")
    source: str | None = Field(None, description="Data source attribution")
    header: bool | None = Field(None, description="Show header section")
    footer: bool | None = Field(None, description="Show footer section")


class DirectLineLabelsConfig(BaseModel):
    """Configuration for direct line labels."""

    fontsize: int | None = Field(None, description="Font size for labels")
    position: Literal["right", "left", "auto"] | None = Field("auto", description="Label position")
    bbox: bool | None = Field(True, description="Add background box to labels")
