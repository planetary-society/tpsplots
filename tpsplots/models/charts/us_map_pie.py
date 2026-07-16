"""US Map Pie chart configuration model.

Covers all kwargs accepted by USMapPieChartView._create_chart.
"""

from typing import Any, Literal

from pydantic import Field, model_validator

from tpsplots.models.mixins import ChartConfigBase


class USMapPieChartConfig(ChartConfigBase):
    """Validated configuration for ``type: us_map_pie`` charts.

    Inherits from ChartConfigBase only (no axis/grid/legend mixins —
    US map pie charts handle their own legend and axes).

    Two input pathways are supported:

    1. **Controller-built pie_data**: provide ``pie_data`` directly (typically
       as a ``{{pie_data}}`` template ref from a controller method that emits
       the dict). Used by FY2026 (see ``nasa_center_workforce_map``).
    2. **CSV-driven columns**: provide ``data`` (a DataFrame template ref) plus
       ``location_column``, ``value_columns``, ``labels``, and ``colors``. The
       view builds the ``pie_data`` dict from those columns. Rows whose
       ``location_column`` value is blank/null are loaded but not plotted.
    """

    type: Literal["us_map_pie"] = Field("us_map_pie", description="Chart type discriminator")

    # --- Data bindings ---
    pie_data: Any = Field(
        None,
        description=(
            "Dict mapping location names to pie chart data dicts "
            "(each with 'values', 'labels', 'colors'). Required unless the "
            "column-oriented fields below are provided."
        ),
    )
    data: Any = Field(
        None,
        description=(
            "DataFrame template reference (e.g. '{{data}}') used with the "
            "column-oriented fields below to assemble pie_data from a CSV. "
            "Ignored when pie_data is provided directly."
        ),
    )
    location_column: str | None = Field(
        None,
        description=(
            "Column name in ``data`` whose values match NASA_CENTERS keys "
            "(full names or abbreviations). Rows with blank/null values in "
            "this column are dropped from plotted pies."
        ),
    )
    value_columns: list[str] | None = Field(
        None,
        description=(
            "Column names in ``data`` to use as pie segment values, one per segment. "
            "Length must equal ``labels`` and ``colors``."
        ),
    )
    labels: list[str] | None = Field(
        None, description="Legend label for each pie segment; aligned with ``value_columns``."
    )
    colors: list[str] | None = Field(
        None,
        description=(
            "Color for each pie segment; aligned with ``value_columns``. "
            "Accepts hex codes or TPS brand names (e.g. 'Neptune Blue')."
        ),
    )

    @model_validator(mode="after")
    def _check_column_inputs(self) -> "USMapPieChartConfig":
        """Enforce the column-oriented field group is internally consistent."""
        location_column = self.location_column
        value_columns = self.value_columns
        labels = self.labels
        colors = self.colors

        if location_column is None and value_columns is None and labels is None and colors is None:
            return self

        if location_column is None or value_columns is None or labels is None or colors is None:
            missing = [
                name
                for name, value in (
                    ("location_column", location_column),
                    ("value_columns", value_columns),
                    ("labels", labels),
                    ("colors", colors),
                )
                if value is None
            ]
            raise ValueError(
                "When using the column-oriented us_map_pie pathway, "
                f"all of location_column/value_columns/labels/colors must be set. Missing: {missing}"
            )

        if not (len(value_columns) == len(labels) == len(colors)):
            raise ValueError(
                "value_columns, labels, and colors must have equal length "
                f"(got {len(value_columns)}, {len(labels)}, {len(colors)})"
            )

        return self

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
        None, description="Matplotlib legend location (loc). Default: 'lower left'"
    )
    pie_edge_color: str | None = Field(
        None, description="Edge color for pie wedges. Default: 'white'"
    )
    pie_edge_width: float | None = Field(
        None, description="Edge line width for pie wedges. Default: 0.5"
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
