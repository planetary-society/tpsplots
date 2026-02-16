"""Line chart configuration model.

Covers all kwargs accepted by LineChartView.line_plot / _create_chart /
_apply_axes_styling / _apply_horizontal_lines.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from tpsplots.models.mixins import (
    AxisMixin,
    ChartConfigBase,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    TickFormatMixin,
)

# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class DirectLineLabelsConfig(BaseModel):
    """Configuration for direct line labels (placed near line endpoints).

    In YAML, ``direct_line_labels`` can be:
    - ``true``/``false`` (parsed as bool, not this model)
    - A dict with these optional keys
    """

    position: Literal["right", "left", "top", "bottom", "above", "below", "auto"] | None = Field(
        "auto", description="Label position relative to line endpoint"
    )
    bbox: bool | None = Field(True, description="Add background box to labels")
    fontsize: int | float | None = Field(None, description="Font size for labels")
    end_point: bool | dict | list | None = Field(
        None,
        description=(
            "Endpoint marker config: True for default, dict for custom style, "
            "or list for per-series config"
        ),
    )
    offset: list | None = Field(None, description="Label offset as [x, y]")


class SeriesConfig(BaseModel):
    """Per-series override configuration (populated from series_0, series_1, etc.)."""

    color: str | None = Field(None, description="Series color")
    linestyle: str | None = Field(None, description="Line style")
    linewidth: float | None = Field(None, description="Line width")
    marker: str | None = Field(None, description="Marker style")
    markersize: float | None = Field(None, description="Marker size")
    label: str | None = Field(None, description="Series label")
    alpha: float | None = Field(None, description="Transparency")

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Main config
# ---------------------------------------------------------------------------


class LineChartConfig(
    AxisMixin,
    GridMixin,
    LegendMixin,
    TickFormatMixin,
    ScaleMixin,
    ChartConfigBase,
):
    """Validated configuration for ``type: line`` charts.

    Inherits shared fields from mixins:
    - AxisMixin: xlim, ylim, xlabel, ylabel, tick_rotation, tick_size, label_size
    - GridMixin: grid, grid_axis
    - LegendMixin: legend
    - TickFormatMixin: x_tick_format, y_tick_format, fiscal_year_ticks, max_xticks
    - ScaleMixin: scale, axis_scale
    - ChartConfigBase: output, title, subtitle, source, figsize, dpi, export_data,
      matplotlib_config
    """

    type: Literal["line"] = Field("line", description="Chart type discriminator")

    # --- Data bindings ---
    x: Any = Field(None, description="X-axis data or column reference")
    y: Any = Field(None, description="Y-axis data or column reference(s)")
    data: Any = Field(None, description="DataFrame reference")

    # --- Right y-axis (dual axis) ---
    y_right: Any = Field(
        None,
        description=(
            "Right y-axis data binding: column reference(s) for secondary axis. "
            "Per-series styling arrays (color, labels, etc.) span both axes in "
            "[left..., right...] order"
        ),
    )
    ylim_right: list | dict | str | None = Field(None, description="Right y-axis limits")
    ylabel_right: str | None = Field(None, description="Right y-axis label text")
    y_tick_format_right: str | None = Field(
        None,
        description=(
            "Python format spec for right y-axis tick labels. "
            "Ignored if scale_right formatting is active"
        ),
    )
    scale_right: Literal["billions", "millions", "thousands", "percentage"] | str | None = Field(
        None, description="Scale formatting for right y-axis values"
    )

    # --- Line styling ---
    color: str | list[str] | None = Field(None, description="Line color(s)")
    linestyle: str | list[str] | None = Field(None, description="Line style(s)")
    linewidth: float | list[float] | None = Field(None, description="Line width(s)")
    marker: str | list[str | None] | None = Field(None, description="Marker style(s)")
    markersize: float | list[float] | None = Field(
        None, description="Marker size(s): single value or per-series list"
    )
    alpha: float | list[float] | None = Field(
        None,
        description=(
            "Line transparency (0.0 = fully transparent, 1.0 = fully opaque). "
            "Single value applies to all lines; list sets per-series transparency"
        ),
    )
    labels: str | list[str | None] | None = Field(None, description="Legend label(s)")

    # --- Series types (semantic styling) ---
    series_types: list[str] | None = Field(
        None,
        description=(
            "Semantic series types that apply default styling per series. "
            "Values: 'prior' (gray dashed, 1.5pt), 'average' (blue solid, 4pt, circle markers), "
            "'current' (Rocket Flame solid, 4pt, circle markers). "
            "List length must match number of y series. Overridden by explicit color/linestyle/etc."
        ),
    )

    # --- Direct line labels ---
    direct_line_labels: bool | DirectLineLabelsConfig | dict | None = Field(
        None,
        description=(
            "Place labels near line endpoints instead of a legend box. Default: False (use legend). "
            "True: enable with auto-positioning. Dict config keys: "
            "position ('right'|'left'|'top'|'bottom'|'auto', default 'auto'), "
            "bbox (background box, default True), fontsize (default from style legend_size), "
            "end_point (True for default circle marker, dict for custom {marker, size, facecolor, "
            "edgecolor, edgewidth, zorder}, or list for per-series config)"
        ),
    )

    # --- Horizontal lines ---
    hlines: float | list | dict | None = Field(
        None, description="Y-values for horizontal reference lines"
    )
    hline_colors: str | list[str] | None = Field(None, description="Colors for horizontal lines")
    hline_styles: str | list[str] | None = Field(
        None, description="Line styles for horizontal lines"
    )
    hline_widths: float | list[float] | None = Field(
        None, description="Line widths for horizontal lines"
    )
    hline_labels: str | list[str] | None = Field(None, description="Labels for horizontal lines")
    hline_alpha: float | list[float] | None = Field(
        None,
        description=(
            "Transparency for horizontal lines (0.0-1.0). Default: 0.7. "
            "Single value or list matching hlines length"
        ),
    )
    hline_label_position: Literal["right", "left", "center"] | None = Field(
        None,
        description=(
            "Horizontal position for hline labels on the plot. "
            "Default: 'right'. Labels auto-adjust vertically to prevent overlap"
        ),
    )
    hline_label_offset: float | None = Field(
        None,
        description=(
            "Horizontal offset for hline labels as fraction of plot width. "
            "Default: 0.02 (2% inset from the edge specified by hline_label_position)"
        ),
    )
    hline_label_fontsize: int | float | None = Field(
        None, description="Font size for horizontal line labels"
    )
    hline_label_bbox: bool | None = Field(
        None,
        description=(
            "Add a white rounded background box with colored border to horizontal line labels. "
            "Default: True. Helps readability when labels overlap data"
        ),
    )

    # --- Custom ticks ---
    xticks: list | None = Field(None, description="Custom x-axis tick positions")
    xticklabels: list[str] | None = Field(None, description="Custom x-axis tick labels")

    # --- Per-series overrides (collected from series_0, series_1, ...) ---
    series_overrides: dict[int, dict | SeriesConfig] | None = Field(
        None,
        description="Per-series override configs (auto-collected from series_N keys)",
    )

    @model_validator(mode="before")
    @classmethod
    def collect_series_overrides(cls, data: Any) -> Any:
        """Collect series_N keys into series_overrides before extra='forbid' runs.

        YAML users write::

            series_0:
              color: red
            series_1:
              linestyle: "--"

        This validator pops those keys from the raw dict and stores them in
        ``series_overrides`` so Pydantic doesn't reject them as unknown fields.
        """
        if isinstance(data, dict):
            overrides: dict[int, Any] = {}
            for key in list(data.keys()):
                if key.startswith("series_") and key[7:].isdigit():
                    overrides[int(key[7:])] = data.pop(key)
            if overrides:
                data["series_overrides"] = overrides
        return data
