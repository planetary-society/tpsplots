"""Chart parameters configuration model.

.. deprecated::
    ``ParametersConfig`` is superseded by per-chart-type config models in
    ``tpsplots.models.charts``.  Use the discriminated ``ChartConfig`` union
    or a specific model (e.g. ``LineChartConfig``) instead.
"""

import warnings
from typing import Any

from pydantic import BaseModel, Field, field_validator

from tpsplots.models.charts.line import DirectLineLabelsConfig


class ParametersConfig(BaseModel):
    """Chart parameters configuration.

    .. deprecated::
        Use per-chart-type config models in ``tpsplots.models.charts`` instead.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        warnings.warn(
            "ParametersConfig is deprecated. Use per-chart-type config models "
            "(e.g. LineChartConfig, BarChartConfig) instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Data mapping - most can be strings (data references) or actual values
    x: str | None = Field(None, description="X-axis data reference")
    y: str | list[str] | None = Field(None, description="Y-axis data reference(s)")
    color: str | list[str] | None = Field(None, description="Color specification")
    linestyle: str | list[str] | None = Field(None, description="Line style specification")
    linewidth: float | list[float] | str | list[str] | None = Field(
        None, description="Line width specification"
    )
    marker: str | list[str] | None = Field(None, description="Marker specification")
    label: str | list[str] | None = Field(None, description="Label specification")

    # Axis configuration
    xlim: list[float] | str | None = Field(
        None, description="X-axis limits [min, max] or data reference"
    )
    ylim: list[float] | str | None = Field(
        None, description="Y-axis limits [min, max] or data reference"
    )
    xlabel: str | None = Field(None, description="X-axis label")
    ylabel: str | None = Field(None, description="Y-axis label")

    # Styling
    label_size: int | str | None = Field(None, description="Label font size or data reference")
    tick_size: int | str | None = Field(None, description="Tick font size or data reference")
    grid: bool | str | None = Field(None, description="Show grid or data reference")
    legend: bool | str | None = Field(None, description="Show legend or data reference")

    # Advanced features
    direct_line_labels: DirectLineLabelsConfig | str | None = Field(
        None, description="Direct line labels config"
    )

    # Export
    export_data: str | None = Field(None, description="Export data reference")

    model_config = {"extra": "allow"}

    @field_validator("ylim", "xlim", mode="before")
    @classmethod
    def validate_limits(cls, v: Any) -> Any:
        """Validate that limits are [min, max] format when they're lists."""
        if v is not None and isinstance(v, list) and len(v) != 2:
            raise ValueError("Limits must be [min, max] format")
        return v
