"""Area chart configuration model."""

from collections.abc import Iterable
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from tpsplots.models.mixins import (
    AnnotationsMixin,
    AxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    TickFormatMixin,
)

Opacity = Annotated[float, Field(ge=0, le=1)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
GEOMETRY_OVERRIDE_KEYS = frozenset(
    {"baseline", "interpolate", "step", "where", "x", "y", "y1", "y2"}
)


def raise_for_geometry_overrides(keys: Iterable[str]) -> None:
    """Reject geometry keys owned by the area renderer."""
    forbidden = GEOMETRY_OVERRIDE_KEYS.intersection(keys)
    if forbidden:
        raise ValueError(f"Area geometry cannot be overridden: {', '.join(sorted(forbidden))}")


class AreaChartConfig(
    AnnotationsMixin,
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ChartConfigBase,
):
    """Validated configuration for ordinary and stacked area charts."""

    type: Literal["area"] = Field("area", description="Chart type discriminator")

    x: Any = Field(None, description="X-axis data or column reference")
    y: Any = Field(None, description="Y-axis data or column reference(s)")
    data: Any = Field(None, description="DataFrame reference")
    stacked: bool = Field(False, description="Stack series cumulatively from a zero baseline")

    color: str | list[str | None] | None = Field(None, description="Area fill color(s)")
    labels: str | list[str | None] | None = Field(None, description="Legend label(s)")
    alpha: Opacity | list[Opacity | None] | None = Field(
        None,
        description=(
            "Area opacity: scalar or per-series list; defaults to 0.65 for ordinary "
            "areas and 1.0 for stacked areas"
        ),
    )
    edgecolor: str | list[str | None] | None = Field(
        "none", description='Closed polygon perimeter color(s); defaults to "none"'
    )
    linewidth: NonNegativeFloat | list[NonNegativeFloat | None] | None = Field(
        0.0, description="Closed polygon perimeter width(s); defaults to 0"
    )
    linestyle: str | list[str | None] | None = Field(
        None, description="Closed polygon perimeter style(s)"
    )

    xticks: list | None = Field(None, description="Custom x-axis tick positions")
    xticklabels: list[str] | None = Field(None, description="Custom x-axis tick labels")

    @field_validator("matplotlib_config")
    @classmethod
    def _reject_geometry_overrides(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            raise_for_geometry_overrides(value)
        return value
