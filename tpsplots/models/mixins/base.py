"""Core base class and template reference utilities for chart config models."""

import re
from typing import Any

from pydantic import BaseModel, Field

TEMPLATE_REF_PATTERN = re.compile(r"\{\{.+\}\}")


def is_template_ref(v: Any) -> bool:
    """Check if a value is a {{...}} template reference string."""
    return isinstance(v, str) and bool(TEMPLATE_REF_PATTERN.fullmatch(v.strip()))


def validate_numeric_or_ref(v: Any) -> Any:
    """Validator for float|str fields: reject strings that aren't template refs.

    Use as a BeforeValidator on numeric fields that may also accept {{...}} refs.
    Rejects ``tick_size: "banana"`` while allowing ``tick_size: "{{ref}}"``.
    """
    if isinstance(v, str) and not is_template_ref(v):
        raise ValueError(f"Expected a number or {{{{...}}}} template reference, got: '{v}'")
    return v


class ChartConfigBase(BaseModel):
    """Base for all per-chart-type config models.

    IMPORTANT: Only this class sets ``model_config``. Mixin models must NOT
    set ``model_config`` — Pydantic v2 does not merge ``model_config`` across
    parent classes; the last class in MRO wins silently.
    See: https://github.com/pydantic/pydantic/issues/9992
    """

    # Required metadata
    output: str = Field(..., description="Base filename for chart outputs")
    title: str = Field(..., description="Chart title")

    # Optional metadata
    subtitle: str | None = Field(
        None, description="Chart subtitle (supports {{variable}} templates)"
    )
    source: str | None = Field(None, description="Data source attribution")

    # Figure-level
    figsize: list[float] | None = Field(
        None,
        description=(
            "Figure size as [width, height] in inches. "
            "Default: [16, 10] desktop, [9, 16] mobile. "
            "Affects layout of titles, axes, and label positioning calculations"
        ),
    )
    dpi: int | None = Field(
        None,
        description=(
            "Dots per inch for output resolution. "
            "Also used in pixel-to-point conversions for label placement (1 pt = dpi/72 px)"
        ),
    )

    # Export
    export_data: Any = Field(
        None,
        description=(
            "Data for CSV export — either a '{{export_df}}' template reference "
            "or a resolved DataFrame after template resolution"
        ),
    )

    # Matplotlib escape hatch — raw kwargs passed through to matplotlib
    matplotlib_config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Raw matplotlib kwargs merged into the plot call after standard field processing. "
            "Keys that overlap with typed fields will override them with a logged warning. "
            "Donut: passed to ax.pie(); line/scatter: passed to ax.plot(); bar: passed to ax.bar()"
        ),
    )

    # Declared here for typing; each concrete subclass defines type: Literal["<name>"]
    type: str

    model_config = {"extra": "forbid", "populate_by_name": True}

    def get_view_method_name(self) -> str:
        """Get the view method name for this chart type."""
        from tpsplots.models.chart_config import CHART_TYPES

        return CHART_TYPES[self.type]
