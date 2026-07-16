"""Validated configuration for treemap charts."""

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import Field, field_validator

from tpsplots.models.mixins import ChartConfigBase

# squarify owns each tile's position and size, so these keys must never reach the
# Rectangle patch — whether through the matplotlib_config escape hatch (guarded
# here) or flattened view kwargs (guarded in TreemapChartView).
GEOMETRY_OVERRIDE_KEYS = frozenset({"x", "y", "xy", "width", "height"})


def raise_for_geometry_overrides(keys: Iterable[str]) -> None:
    """Raise ``ValueError`` if any squarify-owned geometry key is being overridden."""
    forbidden = GEOMETRY_OVERRIDE_KEYS.intersection(keys)
    if forbidden:
        raise ValueError(
            f"Treemap rectangle geometry cannot be overridden: {', '.join(sorted(forbidden))}"
        )


class TreemapChartConfig(ChartConfigBase):
    """Configuration for ``type: treemap`` charts."""

    type: Literal["treemap"] = Field("treemap", description="Chart type discriminator")

    labels: Any = Field(None, description="Labels for each treemap tile")
    values: Any = Field(None, description="Positive values determining treemap tile areas")

    colors: str | list[str] | None = Field(
        None, description="Tile color or colors, using matplotlib or TPS brand names"
    )
    edgecolor: str | None = Field("Polar White", description="Tile border color")
    linewidth: float = Field(2.0, ge=0, description="Tile border width in points")
    alpha: float = Field(1.0, ge=0, le=1, description="Tile opacity")

    show_labels: bool = Field(True, description="Show category labels inside fitting tiles")
    show_percentages: bool = Field(True, description="Show each category's percentage of the total")
    label_min_area_pct: float = Field(
        1.0,
        ge=0,
        le=100,
        description="Minimum total-area percentage eligible for an internal label",
    )
    label_wrap_length: int | None = Field(
        None,
        gt=0,
        description="Maximum characters per line; defaults to the device style",
    )
    label_fontsize: float | None = Field(
        None,
        gt=0,
        description="Label size in points; defaults to the device style",
    )

    @field_validator("matplotlib_config")
    @classmethod
    def _reject_geometry_overrides(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        """Keep squarify-owned rectangle geometry out of the style escape hatch."""
        if value is not None:
            raise_for_geometry_overrides(value)
        return value
