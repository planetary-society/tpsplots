"""Waffle chart configuration model.

WaffleChartView passes ALL remaining kwargs to pywaffle.Waffle.
Common pywaffle params are typed here; for less common ones (icon_style,
icon_legend, block_arranging_style, etc.) use ``pywaffle_config``.
"""

from typing import Any, Literal

from pydantic import Field

from tpsplots.models.mixins import ChartConfigBase, LegendMixin


class WaffleChartConfig(LegendMixin, ChartConfigBase):
    """Validated configuration for ``type: waffle`` charts.

    Inherits from LegendMixin and ChartConfigBase. Since waffle charts
    pass all remaining kwargs to ``pywaffle.Waffle``, common pywaffle
    parameters are typed explicitly. For less-common pywaffle params,
    use the ``pywaffle_config`` escape hatch.
    """

    type: Literal["waffle"] = Field("waffle", description="Chart type discriminator")

    # --- Data bindings ---
    values: Any = Field(None, description="Dict or list of values for waffle blocks")
    labels: list[str] | str | None = Field(None, description="Labels for legend or template ref")

    # --- Common pywaffle parameters (typed) ---
    rows: int | None = Field(
        None,
        description=(
            "Number of rows in the waffle grid. "
            "Default: auto-calculated from total blocks and figure aspect ratio. "
            "If neither rows nor columns is set, both are computed to fit the figsize"
        ),
    )
    columns: int | None = Field(
        None,
        description=(
            "Number of columns in the waffle grid. "
            "Default: auto-calculated from total blocks and figure aspect ratio. "
            "If neither rows nor columns is set, both are computed to fit the figsize"
        ),
    )
    colors: list[str] | None = Field(None, description="Colors for each category")
    vertical: bool | None = Field(
        None,
        description=(
            "Stack blocks vertically (column-first) instead of horizontally (row-first). "
            "Passed directly to pywaffle.Waffle"
        ),
    )
    starting_location: Literal["NW", "NE", "SW", "SE"] | str | None = Field(
        None,
        description=(
            "Corner where block filling begins. "
            "Values: 'NW' (top-left), 'NE' (top-right), 'SW' (bottom-left), 'SE' (bottom-right). "
            "Passed directly to pywaffle.Waffle"
        ),
    )
    interval_ratio_x: float | None = Field(
        None,
        description=(
            "Horizontal gap between waffle blocks as ratio of block width. "
            "Default: pywaffle default (0.2). Increase for more spacing"
        ),
    )
    interval_ratio_y: float | None = Field(
        None,
        description=(
            "Vertical gap between waffle blocks as ratio of block height. "
            "Default: pywaffle default (0.2). Increase for more spacing"
        ),
    )

    # --- Pywaffle escape hatch ---
    pywaffle_config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Raw kwargs passed through to pywaffle.Waffle for less-common parameters "
            "(icon_style, icon_legend, block_arranging_style, etc.)"
        ),
    )
