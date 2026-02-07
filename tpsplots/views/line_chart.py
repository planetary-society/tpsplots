# line_chart.py
import logging
from typing import ClassVar, TypedDict

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.api.extensions import ExtensionArray

from tpsplots.models.charts.line import LineChartConfig

from .chart_view import ChartView
from .mixins import DirectLineLabelsMixin, GridAxisMixin, LineSeriesMixin

logger = logging.getLogger(__name__)


class SeriesTypeStyle(TypedDict, total=False):
    """Type definition for series type style configuration."""

    color: str
    linestyle: str
    marker: str | None
    linewidth: float


class LineChartView(DirectLineLabelsMixin, LineSeriesMixin, GridAxisMixin, ChartView):
    """Specialized view for line charts with a focus on exposing matplotlib's API."""

    CONFIG_CLASS = LineChartConfig

    # Default styling for series_types (semantic series classification)
    # Views apply these when explicit styling isn't provided in YAML
    SERIES_TYPE_STYLES: ClassVar[dict[str, SeriesTypeStyle]] = {
        "prior": {
            "color": "medium_gray",  # References ChartView.COLORS
            "linestyle": "--",
            "marker": None,
            "linewidth": 1.5,
        },
        "average": {
            "color": "blue",  # References ChartView.COLORS
            "linestyle": "-",
            "marker": "o",
            "linewidth": 4.0,
        },
        "current": {
            "color": "Rocket Flame",  # References ChartView.TPS_COLORS
            "linestyle": "-",
            "marker": "o",
            "linewidth": 4.0,
        },
    }

    def _resolve_series_type_color(self, color_name: str) -> str:
        """Resolve a color name to its actual value from COLORS or TPS_COLORS."""
        if color_name in self.COLORS:
            return self.COLORS[color_name]
        if color_name in self.TPS_COLORS:
            return self.TPS_COLORS[color_name]
        return color_name  # Return as-is if not found (might be a hex code)

    def _get_series_type_styles(
        self, series_types: list[str] | None, num_series: int
    ) -> dict[str, list]:
        """
        Get default styling arrays based on series_types metadata.

        Args:
            series_types: List of semantic types ("prior", "average", "current")
            num_series: Number of data series

        Returns:
            Dict with keys: colors, linestyles, markers, linewidths
            Each value is a list matching the number of series
        """
        if not series_types or len(series_types) != num_series:
            return {}

        colors = []
        linestyles = []
        markers = []
        linewidths = []

        for series_type in series_types:
            style_def = self.SERIES_TYPE_STYLES.get(series_type, {})
            color_name = style_def.get("color", "blue")
            colors.append(self._resolve_series_type_color(str(color_name)))
            linestyles.append(style_def.get("linestyle", "-"))
            markers.append(style_def.get("marker"))
            linewidths.append(style_def.get("linewidth", 2.0))

        return {
            "colors": colors,
            "linestyles": linestyles,
            "markers": markers,
            "linewidths": linewidths,
        }

    def _resolve_line_data(self, kwargs):
        """Extract and normalize x/y data from kwargs."""
        data = kwargs.pop("data", kwargs.pop("df", None))
        x = kwargs.pop("x", None)
        y = kwargs.pop("y", None)

        if data is not None:
            x_data = data[x] if isinstance(x, str) else x
            if isinstance(y, (list, tuple)) and all(isinstance(item, str) for item in y):
                y_data = [data[col] for col in y]
            elif isinstance(y, str):
                y_data = [data[y]]
            else:
                y_data = y
        else:
            x_data = x
            y_data = y

        if y_data is None and isinstance(x_data, (list, tuple, np.ndarray, pd.Series, ExtensionArray)):
            y_data = [x_data]
            x_data = np.arange(len(x_data))
        else:
            y_data = self._coerce_series_list(y_data)

        return x_data, y_data

    def _resolve_line_style_options(self, kwargs, style, num_series):
        """Extract line style options with series-type defaults."""
        color = kwargs.pop("color", kwargs.pop("c", None))
        linestyle = kwargs.pop("linestyle", kwargs.pop("ls", None))
        linewidth = kwargs.pop("linewidth", kwargs.pop("lw", None))
        markersize = kwargs.pop("markersize", kwargs.pop("ms", style["marker_size"]))
        marker = kwargs.pop("marker", None)
        alpha = kwargs.pop("alpha", None)
        label = kwargs.pop("label", kwargs.pop("labels", None))
        series_types = kwargs.pop("series_types", None)

        type_styles = self._get_series_type_styles(series_types, num_series)
        if type_styles:
            if color is None:
                color = type_styles["colors"]
            if linestyle is None:
                linestyle = type_styles["linestyles"]
            if marker is None:
                marker = type_styles["markers"]
            if linewidth is None:
                linewidth = type_styles["linewidths"]

        if linewidth is None:
            linewidth = style["line_width"]

        return {
            "color": color,
            "linestyle": linestyle,
            "linewidth": linewidth,
            "markersize": markersize,
            "marker": marker,
            "alpha": alpha,
            "label": label,
        }

    def _plot_line_series(self, ax, x_data, y_data, style_options, kwargs):
        """Plot each line series and collect color/label metadata."""
        num_series = len(y_data) if y_data else 0

        line_colors = []
        line_labels = []

        linestyles = self._normalize_series_param(style_options["linestyle"], num_series)
        markers = self._normalize_series_param(style_options["marker"], num_series)
        alphas = self._normalize_series_param(style_options["alpha"], num_series)
        linewidths = self._normalize_series_param(style_options["linewidth"], num_series)

        for i, y_series in enumerate(y_data):
            plot_kwargs = {}

            color = style_options["color"]
            if isinstance(color, (list, tuple)) and i < len(color):
                series_color = color[i]
                plot_kwargs["color"] = series_color
            elif isinstance(color, str):
                series_color = color
                plot_kwargs["color"] = series_color
            else:
                series_color = ax._get_lines.get_next_color()
                plot_kwargs["color"] = series_color

            if linestyles[i] is not None:
                plot_kwargs["linestyle"] = linestyles[i]
            if markers[i] is not None:
                plot_kwargs["marker"] = markers[i]
            if alphas[i] is not None:
                plot_kwargs["alpha"] = alphas[i]
            if linewidths[i] is not None:
                plot_kwargs["linewidth"] = linewidths[i]

            label = style_options["label"]
            if isinstance(label, (list, tuple)) and i < len(label):
                series_label = label[i]
                plot_kwargs["label"] = series_label
            elif isinstance(label, str) and i == 0:
                series_label = label
                plot_kwargs["label"] = series_label
            elif label is None:
                series_label = f"Series {i + 1}"
                plot_kwargs["label"] = series_label
            else:
                series_label = None

            line_colors.append(series_color)
            line_labels.append(series_label)

            plot_kwargs["markersize"] = style_options["markersize"]

            series_key = f"series_{i}"
            if series_key in kwargs:
                plot_kwargs.update(kwargs.pop(series_key))

            ax.plot(x_data, y_series, **plot_kwargs)

        return line_colors, line_labels

    def line_plot(self, metadata, stem, **kwargs):
        """
        Generate line charts for both desktop and mobile versions.

        Parameters
        ----------
        metadata : dict
            Chart metadata containing:
            - title : str - Main chart title
            - subtitle : str - Chart subtitle (optional)
            - source : str - Data source attribution (optional)

        stem : str
            Base filename for output files (without extension)

        **kwargs : dict
            Additional parameters for customizing the chart:

            Data Parameters:
            ----------------
            x : array-like or str
                X-axis data. Can be:
                - List/array of values for x-axis
                - Column name if 'data' DataFrame is provided
                - If None, uses indices for y data

            y : array-like, list of arrays, or str/list of str
                Y-axis data. Can be:
                - Single array for one line
                - List of arrays for multiple lines
                - Column name(s) if 'data' DataFrame is provided

            data : pd.DataFrame (optional)
                DataFrame containing the data columns
                Also accepts 'df' as parameter name

            Styling Parameters:
            -------------------
            color : str, list of str
                Line colors. Can be single color or list for multiple lines
                Accepts standard matplotlib colors or ChartView.COLORS keys
                Also accepts 'c' as parameter name

            linestyle : str, list of str
                Line styles ('-', '--', ':', '-.', etc.)
                Also accepts 'ls' as parameter name

            linewidth : float
                Width of lines (default from style)
                Also accepts 'lw' as parameter name

            marker : str, list of str
                Marker styles ('o', 's', '^', None, etc.)
                Can be single marker or list for multiple lines

            markersize : float
                Size of markers (default from style)
                Also accepts 'ms' as parameter name

            alpha : float, list of float
                Transparency (0=transparent, 1=opaque)
                Can be single value or list for multiple lines

            label : str, list of str
                Legend labels for lines
                Also accepts 'labels' as parameter name

            Axis Configuration:
            -------------------
            xlim : tuple or dict
                X-axis limits (min, max) or dict with kwargs for set_xlim

            ylim : tuple or dict
                Y-axis limits (min, max) or dict with kwargs for set_ylim

            xlabel : str
                Label for x-axis

            ylabel : str
                Label for y-axis

            xticks : array-like
                Custom x-axis tick positions

            xticklabels : list of str
                Custom x-axis tick labels

            max_xticks : int
                Maximum number of x-axis ticks (for automatic spacing)

            tick_rotation : float
                Rotation angle for x-axis tick labels (default from style)

            tick_size : float
                Font size for tick labels (default from style)

            x_tick_format : str
                Python format spec for x-axis ticks (e.g., ".1f", ",.0f")
                Also accepts 'x_axis_format' as an alias.

            y_tick_format : str
                Python format spec for y-axis ticks (e.g., ",.0f")
                Also accepts 'y_axis_format' as an alias.

            Grid and Formatting:
            --------------------
            grid : bool
                Whether to show grid lines

            scale : str
                Apply scale formatting to axis ('billions', 'millions', 'thousands')

            axis_scale : str
                Which axis to apply scale to ('x', 'y', or 'both', default='y')

            fiscal_year_ticks : bool
                Whether to format x-axis dates as fiscal years (default=True)

            Legend:
            -------
            legend : bool or dict
                Show legend (True/False) or dict with legend kwargs:
                - loc : str - Legend location
                - fontsize : int - Legend font size
                - title : str - Legend title
                - ncol : int - Number of columns
                - frameon : bool - Show legend frame

            direct_line_labels : bool or dict
                Place labels directly on chart near line endpoints instead of legend box.
                - False (default): Use traditional legend
                - True: Enable direct line labels with default settings
                - dict: Advanced configuration:
                  - position : str - Label position ('right', 'left', 'top', 'bottom', 'auto')
                  - bbox : bool - Add background box to labels (default True)
                  - fontsize : int - Label font size (default from style)
                  - end_point : bool, dict, or list - Draw marker at line endpoint
                    - True: Show default circular marker for all series
                    - dict: Custom style for all series with options:
                      - marker : str - Marker shape ('o', 's', '^', 'D', etc.)
                      - size : float - Marker size in points
                      - facecolor : str - Fill color (defaults to line color)
                      - edgecolor : str - Border color (default 'white')
                      - edgewidth : float - Border width (default 1.5)
                      - zorder : int - Draw order (default 9)
                    - list: Per-series config, each element can be False, True, or dict

            Horizontal Lines:
            -----------------
            hlines : float, list, or dict
                Y-values for horizontal reference lines
                Can be:
                - Single value
                - List of values
                - Dict mapping y-values to line kwargs
                Also accepts 'horizontal_lines' as parameter name

            hline_colors : str or list
                Colors for horizontal lines

            hline_styles : str or list
                Line styles for horizontal lines

            hline_widths : float or list
                Line widths for horizontal lines

            hline_labels : str or list
                Labels for horizontal lines (displayed directly on plot)

            hline_alpha : float or list
                Alpha values for horizontal lines

            hline_label_position : str
                Position for line labels ('right', 'left', 'center')

            hline_label_offset : float
                Horizontal offset for labels from edge (fraction of plot width)

            hline_label_fontsize : int
                Font size for line labels

            hline_label_bbox : bool
                Whether to add background box to line labels

            Export and Output:
            ------------------
            export_data : pd.DataFrame
                DataFrame to export as CSV alongside charts

            figsize : tuple
                Figure size (width, height) in inches

            dpi : int
                Dots per inch for output resolution

            series_<n> : dict
                Override parameters for specific series (e.g., series_0, series_1)

        Returns
        -------
        dict
            Dictionary containing generated figure objects:
            - 'desktop' : matplotlib.figure.Figure - Desktop version
            - 'mobile' : matplotlib.figure.Figure - Mobile version

        Examples
        --------
        Basic line chart with two series:

        >>> line_view.line_plot(
        ...     metadata={"title": "Sales Over Time"},
        ...     stem="sales_chart",
        ...     x=["Jan", "Feb", "Mar"],
        ...     y=[[100, 150, 130], [80, 110, 140]],
        ...     label=["Product A", "Product B"],
        ...     color=["blue", "red"],
        ... )

        Using DataFrame input:

        >>> df = pd.DataFrame({"Month": ["Jan", "Feb", "Mar"], "Sales": [100, 150, 130]})
        >>> line_view.line_plot(
        ...     metadata={"title": "Monthly Sales"},
        ...     stem="monthly_sales",
        ...     data=df,
        ...     x="Month",
        ...     y="Sales",
        ... )

        With horizontal reference line:

        >>> line_view.line_plot(
        ...     metadata={"title": "Performance vs Target"},
        ...     stem="performance",
        ...     x=months,
        ...     y=values,
        ...     hlines=100,
        ...     hline_labels="Target",
        ...     hline_colors="red",
        ... )

        With direct line labels and endpoint markers:

        >>> line_view.line_plot(
        ...     metadata={"title": "Budget Comparison"},
        ...     stem="budget",
        ...     x=years,
        ...     y=[proposed, actual],
        ...     label=["Proposed", "Actual"],
        ...     legend=False,
        ...     direct_line_labels={
        ...         "position": "right",
        ...         "fontsize": 10,
        ...         "end_point": {"marker": "o", "size": 8},
        ...     },
        ... )

        With per-series endpoint styles:

        >>> line_view.line_plot(
        ...     metadata={"title": "Multi-series"},
        ...     stem="multi",
        ...     x=dates,
        ...     y=[series_a, series_b],
        ...     label=["Series A", "Series B"],
        ...     legend=False,
        ...     direct_line_labels={
        ...         "position": "right",
        ...         "end_point": [
        ...             {"marker": "o", "size": 8},  # Series A: circle
        ...             {"marker": "s", "size": 10},  # Series B: square
        ...         ],
        ...     },
        ... )
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a line plot with appropriate styling.
        """
        # Set up figure and extract metadata using base class helpers
        fig, ax = self._setup_figure(style, kwargs)
        self._extract_metadata_from_kwargs(metadata, kwargs)

        x_data, y_data = self._resolve_line_data(kwargs)

        style_options = self._resolve_line_style_options(kwargs, style, len(y_data) if y_data else 0)

        line_colors = []
        line_labels = []
        if x_data is not None and y_data is not None:
            line_colors, line_labels = self._plot_line_series(
                ax,
                x_data,
                y_data,
                style_options,
                kwargs,
            )

        # Apply standard styling to the axes
        self._apply_axes_styling(
            ax,
            metadata,
            style,
            x_data=x_data,
            y_data=y_data,
            line_colors=line_colors,
            line_labels=line_labels,
            markersize=style_options["markersize"],
            fig=fig,
            **kwargs,
        )

        self._adjust_layout_for_header_footer(fig, metadata, style)

        # Disable clipping on line artists so markers at axis edges render fully
        # (done after layout adjustment to avoid affecting tight_layout calculations)
        for line in ax.get_lines():
            line.set_clip_on(False)

        return fig

    def _extract_axes_styling_options(self, style, kwargs):
        """Pop axis/style options for line chart axis rendering."""
        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        xticks = kwargs.pop("xticks", None)
        xticklabels = kwargs.pop("xticklabels", None)
        max_xticks = kwargs.pop("max_xticks", style.get("max_ticks"))
        x_tick_format, y_tick_format = self._pop_axis_tick_format_kwargs(kwargs)
        x_data = kwargs.pop("x_data", None)

        grid = kwargs.pop("grid", None)
        tick_rotation = kwargs.pop("tick_rotation", style["tick_rotation"])
        tick_size = kwargs.pop("tick_size", style["tick_size"])
        label_size = kwargs.pop("label_size", style["label_size"])
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        scale = kwargs.pop("scale", None)
        axis_scale = kwargs.pop("axis_scale", "y")
        fiscal_year_ticks = kwargs.pop("fiscal_year_ticks", True)

        legend = kwargs.pop("legend", True)
        direct_line_labels = kwargs.pop("direct_line_labels", False)
        y_data = kwargs.pop("y_data", None)
        line_colors = kwargs.pop("line_colors", [])
        line_labels = kwargs.pop("line_labels", [])
        markersize = kwargs.pop("markersize", style.get("marker_size", 6))

        return {
            "xlim": xlim,
            "ylim": ylim,
            "xticks": xticks,
            "xticklabels": xticklabels,
            "max_xticks": max_xticks,
            "x_tick_format": x_tick_format,
            "y_tick_format": y_tick_format,
            "x_data": x_data,
            "grid": grid,
            "tick_rotation": tick_rotation,
            "tick_size": tick_size,
            "label_size": label_size,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "scale": scale,
            "axis_scale": axis_scale,
            "fiscal_year_ticks": fiscal_year_ticks,
            "legend": legend,
            "direct_line_labels": direct_line_labels,
            "y_data": y_data,
            "line_colors": line_colors,
            "line_labels": line_labels,
            "markersize": markersize,
        }

    def _apply_line_label_grid_tick_styling(self, ax, style, opts):
        """Apply shared labels/grid/ticks while preserving legacy line behavior."""
        grid = opts["grid"]
        if isinstance(grid, dict):
            self._apply_axis_labels(
                ax,
                xlabel=opts["xlabel"],
                ylabel=opts["ylabel"],
                label_size=opts["label_size"],
                style_type=style["type"],
                italic=False,
            )
            ax.grid(**grid)
            self._apply_tick_styling(
                ax,
                tick_size=opts["tick_size"],
                tick_rotation=opts["tick_rotation"],
                style_type="desktop",
            )
            return

        if grid is None:
            effective_grid = style.get("grid")
            effective_grid_axis = style.get("grid_axis")
        elif grid:
            effective_grid = True
            effective_grid_axis = "both"
        else:
            effective_grid = False
            effective_grid_axis = style.get("grid_axis")

        self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=opts["xlabel"],
            ylabel=opts["ylabel"],
            label_size=opts["label_size"],
            tick_size=opts["tick_size"],
            tick_rotation=opts["tick_rotation"],
            grid=effective_grid,
            grid_axis=effective_grid_axis,
            grid_linestyle="-",
            grid_linewidth=0.8,
            italic=False,
            scale_ticks_for_mobile=False,
        )

    def _apply_line_axis_limits(self, ax, xlim, ylim, x_data):
        """Apply x/y limits with datetime conversion for year-like x limits."""
        if xlim:
            xlim = self._convert_xlim_to_datetime(xlim, x_data)
        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)

    def _apply_line_tick_formatting(self, ax, style, opts):
        """Apply x-axis date/fiscal/categorical tick formatting."""
        x_data = opts["x_data"]
        tick_rotation = opts["tick_rotation"]
        tick_size = opts["tick_size"]
        max_xticks = opts["max_xticks"]
        fiscal_year_ticks = opts["fiscal_year_ticks"]

        if fiscal_year_ticks and x_data is not None and self._contains_dates(x_data):
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
            return

        if x_data is not None and self._contains_dates(x_data):
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)
            return

        plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
        plt.setp(ax.get_yticklabels(), fontsize=tick_size)

        is_categorical = x_data is not None and len(x_data) > 0 and isinstance(next(iter(x_data)), str)
        if max_xticks and not is_categorical:
            ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
        elif is_categorical and max_xticks and len(x_data) > max_xticks:
            step = len(x_data) // max_xticks + 1
            tick_positions = list(range(0, len(x_data), step))
            ax.set_xticks(tick_positions)
            try:
                ax.set_xticklabels([list(x_data)[i] for i in tick_positions])
            except Exception:
                logger.warning("Could not set categorical xticklabels.")

    def _apply_line_scale_and_custom_ticks(self, ax, opts):
        """Apply scale formatters, custom ticks, and format specs."""
        scaled_x = False
        scaled_y = False
        if opts["scale"]:
            if opts["axis_scale"] == "both":
                self._apply_scale_formatter(
                    ax, opts["scale"], "x", tick_format=opts["x_tick_format"]
                )
                self._apply_scale_formatter(
                    ax, opts["scale"], "y", tick_format=opts["y_tick_format"]
                )
                scaled_x = True
                scaled_y = True
            elif opts["axis_scale"] == "x":
                self._apply_scale_formatter(
                    ax, opts["scale"], "x", tick_format=opts["x_tick_format"]
                )
                scaled_x = True
            else:
                self._apply_scale_formatter(
                    ax, opts["scale"], "y", tick_format=opts["y_tick_format"]
                )
                scaled_y = True

        if opts["xticks"] is not None:
            ax.set_xticks(opts["xticks"])
            if opts["xticklabels"] is not None:
                ax.set_xticklabels(opts["xticklabels"])
            elif all(
                isinstance(x, (int, float)) and float(x).is_integer() for x in opts["xticks"]
            ):
                ax.set_xticklabels([f"{int(x)}" for x in opts["xticks"]])

        self._apply_tick_format_specs(
            ax,
            x_tick_format=opts["x_tick_format"] if not scaled_x else None,
            y_tick_format=opts["y_tick_format"] if not scaled_y else None,
            has_explicit_xticklabels=opts["xticklabels"] is not None,
        )

    def _apply_line_label_strategy(self, ax, style, fig, opts, kwargs):
        """Apply direct line labels or legend based on options."""
        if opts["direct_line_labels"] and opts["y_data"] is not None and opts["line_colors"] and opts[
            "line_labels"
        ]:
            if fig:
                try:
                    fig.tight_layout(rect=[0, 0.0, 1, 1.0])
                    fig.canvas.draw()
                except Exception as e:
                    logger.warning(f"Failed to draw canvas before label placement: {e}")

            self._add_direct_line_endpoint_labels(
                ax,
                opts["x_data"],
                opts["y_data"],
                opts["line_labels"],
                opts["line_colors"],
                style,
                fig=fig,
                direct_line_labels=opts["direct_line_labels"],
                markersize=opts["markersize"],
                **kwargs,
            )
            return

        if opts["legend"]:
            legend_kwargs = {"fontsize": style["legend_size"]}
            if isinstance(opts["legend"], dict):
                legend_kwargs.update(opts["legend"])
            handles, _labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(**legend_kwargs)

    def _apply_axes_styling(self, ax, metadata, style, fig=None, **kwargs):
        """Apply consistent styling to line chart axes."""
        opts = self._extract_axes_styling_options(style, kwargs)
        self._apply_line_label_grid_tick_styling(ax, style, opts)
        self._apply_line_axis_limits(ax, opts["xlim"], opts["ylim"], opts["x_data"])
        self._apply_line_tick_formatting(ax, style, opts)
        self._apply_line_scale_and_custom_ticks(ax, opts)
        self._apply_horizontal_lines(ax, **kwargs)
        self._apply_line_label_strategy(ax, style, fig, opts, kwargs)

    def _apply_horizontal_lines(self, ax, **kwargs):
        """
        Add horizontal reference lines with labels positioned directly on the lines.

        Args:
            ax: Matplotlib axes object
            **kwargs: Horizontal line parameters
                - hlines: float, list, or dict - Y-values for horizontal lines
                - hline_colors: str or list - Colors for horizontal lines
                - hline_styles: str or list - Line styles for horizontal lines
                - hline_widths: float or list - Line widths for horizontal lines
                - hline_labels: str or list - Labels for horizontal lines
                - hline_alpha: float or list - Alpha values for horizontal lines
                - hline_label_position: str - Position for labels ('right', 'left', 'center')
                - hline_label_offset: float - Horizontal offset for labels from edge
                - hline_label_fontsize: int - Font size for line labels
                - hline_label_bbox: bool - Whether to add background box to labels
        """
        hlines = kwargs.pop("hlines", kwargs.pop("horizontal_lines", None))

        if hlines is None:
            return

        # Get label positioning parameters
        label_position = kwargs.pop("hline_label_position", "right")
        label_offset = kwargs.pop("hline_label_offset", 0.02)  # As fraction of plot width
        label_fontsize = kwargs.pop("hline_label_fontsize", 12)
        label_bbox = kwargs.pop("hline_label_bbox", True)

        # Handle dict format for more complex styling
        if isinstance(hlines, dict):
            y_values = []
            labels = []

            for y_value, line_kwargs in hlines.items():
                # Extract label from line_kwargs if present
                label = line_kwargs.pop("label", None)

                # Set default line styling
                default_kwargs = {
                    "color": "gray",
                    "linestyle": "--",
                    "linewidth": 2,
                    "alpha": 0.7,
                    "zorder": 0,
                }
                default_kwargs.update(line_kwargs)

                # Draw the line (without label since we'll add it manually)
                ax.axhline(y=y_value, **default_kwargs)

                # Store for label positioning
                if label:
                    y_values.append(y_value)
                    labels.append((label, default_kwargs.get("color", "gray")))

            # Add direct labels
            if y_values and labels:
                self._add_direct_line_labels(
                    ax, y_values, labels, label_position, label_offset, label_fontsize, label_bbox
                )
            return

        # Handle single value or list of values
        if not isinstance(hlines, (list, tuple)):
            hlines = [hlines]

        # Extract styling parameters with defaults
        hline_colors = kwargs.pop("hline_colors", ["gray"] * len(hlines))
        hline_styles = kwargs.pop("hline_styles", ["--"] * len(hlines))
        hline_widths = kwargs.pop("hline_widths", [2] * len(hlines))
        hline_labels = kwargs.pop("hline_labels", [None] * len(hlines))
        hline_alpha = kwargs.pop("hline_alpha", [0.7] * len(hlines))

        # Ensure all styling parameters are lists of correct length
        def ensure_list(param, length):
            if not isinstance(param, (list, tuple)):
                return [param] * length
            elif len(param) < length:
                return list(param) + [param[-1]] * (length - len(param))
            return param[:length]

        num_lines = len(hlines)
        hline_colors = ensure_list(hline_colors, num_lines)
        hline_styles = ensure_list(hline_styles, num_lines)
        hline_widths = ensure_list(hline_widths, num_lines)
        hline_alpha = ensure_list(hline_alpha, num_lines)
        hline_labels = ensure_list(hline_labels, num_lines)

        # Add each horizontal line (without legend labels)
        for i, y_value in enumerate(hlines):
            ax.axhline(
                y=y_value,
                color=hline_colors[i],
                linestyle=hline_styles[i],
                linewidth=hline_widths[i],
                alpha=hline_alpha[i],
                zorder=0,
            )

        # Add direct labels for lines that have them
        labeled_y_values = []
        labeled_info = []

        for i, (y_value, label) in enumerate(zip(hlines, hline_labels, strict=False)):
            if label:
                labeled_y_values.append(y_value)
                labeled_info.append((label, hline_colors[i]))

        if labeled_y_values:
            self._add_direct_line_labels(
                ax,
                labeled_y_values,
                labeled_info,
                label_position,
                label_offset,
                label_fontsize,
                label_bbox,
            )
