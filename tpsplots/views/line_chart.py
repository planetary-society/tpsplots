# line_chart.py
import logging
import math
from typing import ClassVar, TypedDict

import matplotlib.dates as mdates
import matplotlib.path as mpath
import matplotlib.pyplot as plt

# Imports for advanced geometry and transformations
import matplotlib.transforms
import numpy as np
import pandas as pd
from matplotlib.transforms import Bbox
from pandas.api.extensions import ExtensionArray

from .chart_view import ChartView
from .mixins import GridAxisMixin

logger = logging.getLogger(__name__)


class SeriesTypeStyle(TypedDict, total=False):
    """Type definition for series type style configuration."""

    color: str
    linestyle: str
    marker: str | None
    linewidth: float


class LineChartView(GridAxisMixin, ChartView):
    """Specialized view for line charts with a focus on exposing matplotlib's API."""

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

        # Extract data and handle DataFrame input if provided
        data = kwargs.pop("data", kwargs.pop("df", None))
        x = kwargs.pop("x", None)
        y = kwargs.pop("y", None)

        # Handle DataFrame columns or direct data arrays
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

        # Handle single y series
        if y_data is None and isinstance(
            x_data, (list, tuple, np.ndarray, pd.Series, ExtensionArray)
        ):
            y_data = [x_data]
            x_data = np.arange(len(x_data))

        # Make sure y_data is a list of series for consistent handling
        if (
            y_data is not None
            and not isinstance(y_data, (list, tuple))
            and isinstance(y_data, (pd.Series, np.ndarray, ExtensionArray))
        ):
            y_data = [y_data]

        # Extract styling parameters
        color = kwargs.pop("color", kwargs.pop("c", None))
        linestyle = kwargs.pop("linestyle", kwargs.pop("ls", None))
        linewidth = kwargs.pop("linewidth", kwargs.pop("lw", None))

        # Extract markersize, crucial for label placement calculations
        markersize = kwargs.pop("markersize", kwargs.pop("ms", style["marker_size"]))
        marker = kwargs.pop("marker", None)
        alpha = kwargs.pop("alpha", None)
        label = kwargs.pop("label", kwargs.pop("labels", None))

        # Extract series_types for semantic styling defaults
        series_types = kwargs.pop("series_types", None)

        # Apply series_types defaults when explicit styling isn't provided
        num_series = len(y_data) if y_data else 0
        type_styles = self._get_series_type_styles(series_types, num_series)

        if type_styles:
            # Use series_types styling as defaults when explicit values not provided
            if color is None:
                color = type_styles["colors"]
            if linestyle is None:
                linestyle = type_styles["linestyles"]
            if marker is None:
                marker = type_styles["markers"]
            if linewidth is None:
                linewidth = type_styles["linewidths"]

        # Fall back to style defaults if still None
        if linewidth is None:
            linewidth = style["line_width"]

        # Store line information for direct labeling
        line_colors = []
        line_labels = []

        # Plot each data series
        if x_data is not None and y_data is not None:
            for i, y_series in enumerate(y_data):
                # Build plot kwargs for this series
                plot_kwargs = {}

                # Handle colors
                if isinstance(color, (list, tuple)) and i < len(color):
                    plot_kwargs["color"] = color[i]
                    series_color = color[i]
                elif color is not None and isinstance(color, str):
                    # Apply single color to all if it's a string
                    plot_kwargs["color"] = color
                    series_color = color
                else:
                    # Use default matplotlib color cycle
                    series_color = ax._get_lines.get_next_color()
                    plot_kwargs["color"] = series_color

                # Handle linestyle, marker, alpha, linewidth
                if isinstance(linestyle, (list, tuple)) and i < len(linestyle):
                    plot_kwargs["linestyle"] = linestyle[i]
                elif linestyle is not None:
                    plot_kwargs["linestyle"] = linestyle

                if isinstance(marker, (list, tuple)) and i < len(marker):
                    plot_kwargs["marker"] = marker[i]
                elif marker is not None:
                    plot_kwargs["marker"] = marker

                if isinstance(alpha, (list, tuple)) and i < len(alpha):
                    plot_kwargs["alpha"] = alpha[i]
                elif alpha is not None:
                    plot_kwargs["alpha"] = alpha

                # Handle per-series linewidth
                if isinstance(linewidth, (list, tuple)) and i < len(linewidth):
                    plot_kwargs["linewidth"] = linewidth[i]
                elif linewidth is not None:
                    plot_kwargs["linewidth"] = linewidth

                # Handle labels
                if isinstance(label, (list, tuple)) and i < len(label):
                    plot_kwargs["label"] = label[i]
                    series_label = label[i]
                elif label is not None and i == 0 and isinstance(label, str):
                    plot_kwargs["label"] = label
                    series_label = label
                else:
                    # Only assign default label if 'label' parameter was not provided at all
                    if label is None:
                        series_label = f"Series {i + 1}"
                        plot_kwargs["label"] = series_label
                    else:
                        series_label = None

                # Always store for direct labeling to maintain alignment with y_series
                # (None labels will be skipped during actual label placement)
                line_colors.append(series_color)
                line_labels.append(series_label)

                # Set markersize (linewidth is handled above per-series)
                plot_kwargs["markersize"] = markersize

                # Apply any series-specific overrides
                series_key = f"series_{i}"
                if series_key in kwargs:
                    plot_kwargs.update(kwargs.pop(series_key))

                # Plot this series
                ax.plot(x_data, y_series, **plot_kwargs)

        # Apply standard styling to the axes
        self._apply_axes_styling(
            ax,
            metadata,
            style,
            x_data=x_data,
            y_data=y_data,
            line_colors=line_colors,
            line_labels=line_labels,
            markersize=markersize,
            fig=fig,
            **kwargs,
        )

        self._adjust_layout_for_header_footer(fig, metadata, style)

        # Disable clipping on line artists so markers at axis edges render fully
        # (done after layout adjustment to avoid affecting tight_layout calculations)
        for line in ax.get_lines():
            line.set_clip_on(False)

        return fig

    def _apply_axes_styling(self, ax, metadata, style, fig=None, **kwargs):
        """
        Apply consistent styling to the axes.
        """
        # Extract parameters
        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        xticks = kwargs.pop("xticks", None)
        xticklabels = kwargs.pop("xticklabels", None)
        max_xticks = kwargs.pop("max_xticks", style.get("max_ticks"))
        x_data = kwargs.pop("x_data", None)

        grid = kwargs.pop("grid", None)
        tick_rotation = kwargs.pop("tick_rotation", style["tick_rotation"])
        tick_size = kwargs.pop("tick_size", style["tick_size"])
        label_size = kwargs.pop("label_size", style["label_size"])
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        scale = kwargs.pop("scale", None)
        axis_scale = kwargs.pop("axis_scale", "y")

        legend = kwargs.pop("legend", True)
        direct_line_labels = kwargs.pop("direct_line_labels", False)
        y_data = kwargs.pop("y_data", None)
        line_colors = kwargs.pop("line_colors", [])
        line_labels = kwargs.pop("line_labels", [])
        # Ensure markersize is available (passed from _create_chart)
        kwargs.get("markersize", style.get("marker_size", 6))

        # Apply axis labels using mixin
        self._apply_axis_labels(
            ax,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            style_type=style["type"],
            italic=False,
        )

        if grid or style.get("grid"):
            if grid:
                if isinstance(grid, bool):
                    ax.grid(grid)
                else:
                    ax.grid(**grid)
            else:
                grid_args = {"axis": style.get("grid_axis")}
                ax.grid(**grid_args)

        ax.tick_params(axis="x", labelsize=tick_size)
        ax.tick_params(axis="y", labelsize=tick_size)

        # Apply axis limits BEFORE tick formatting so year range is computed correctly
        if xlim:
            # Convert integer years to datetime if x_data contains datetime objects
            xlim = self._convert_xlim_to_datetime(xlim, x_data)
            if isinstance(xlim, dict):
                ax.set_xlim(**xlim)
            else:
                ax.set_xlim(xlim)
        if ylim:
            if isinstance(ylim, dict):
                ax.set_ylim(**ylim)
            else:
                ax.set_ylim(ylim)

        # Apply appropriate tick formatting (AFTER xlim/ylim so year range is correct)
        fiscal_year_ticks = kwargs.pop("fiscal_year_ticks", True)

        if fiscal_year_ticks and x_data is not None and self._contains_dates(x_data):
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
        elif x_data is not None and self._contains_dates(x_data):
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)
        else:
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)

            is_categorical = (
                x_data is not None and len(x_data) > 0 and isinstance(next(iter(x_data)), str)
            )

            if max_xticks and not is_categorical:
                ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
            elif is_categorical and max_xticks and len(x_data) > max_xticks:
                step = len(x_data) // max_xticks + 1
                tick_positions = list(range(0, len(x_data), step))
                ax.set_xticks(tick_positions)
                # Handle potential indexing issues if x_data is not a standard list
                try:
                    ax.set_xticklabels([list(x_data)[i] for i in tick_positions])
                except Exception:
                    logger.warning("Could not set categorical xticklabels.")

        # Apply scale formatter
        if scale:
            self._apply_scale_formatter(ax, scale, axis_scale)

        if xticks is not None:
            ax.set_xticks(xticks)
            if xticklabels is not None:
                ax.set_xticklabels(xticklabels)
            elif all(isinstance(x, (int, float)) and float(x).is_integer() for x in xticks):
                ax.set_xticklabels([f"{int(x)}" for x in xticks])

        # Apply horizontal lines if specified
        self._apply_horizontal_lines(ax, **kwargs)

        # Handle labeling - either direct line labels or traditional legend
        if direct_line_labels and y_data is not None and line_colors and line_labels:
            # CRITICAL: We must finalize the layout and draw the canvas to get the renderer
            # and accurate transformations before calculating label positions in display coordinates.
            if fig:
                try:
                    # Applying a preliminary tight_layout helps finalize axes positions before drawing.
                    # _adjust_layout_for_header_footer will apply the final layout later.
                    fig.tight_layout(rect=[0, 0.0, 1, 1.0])
                    fig.canvas.draw()
                except Exception as e:
                    logger.warning(f"Failed to draw canvas before label placement: {e}")

            # Use direct line endpoint labels instead of legend
            # MODIFIED: Pass fig and kwargs (which contains markersize)
            self._add_direct_line_endpoint_labels(
                ax,
                x_data,
                y_data,
                line_labels,
                line_colors,
                style,
                fig=fig,
                direct_line_labels=direct_line_labels,
                **kwargs,
            )
        elif legend:
            # Use traditional legend
            legend_kwargs = {"fontsize": style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)
            # Check if there are handles to display
            handles, _labels = ax.get_legend_handles_labels()
            if handles:
                ax.legend(**legend_kwargs)

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

    def _add_direct_line_labels(
        self, ax, y_values, label_info, position="right", offset=0.02, fontsize=12, add_bbox=True
    ):
        """
        Add labels directly on horizontal lines.

        Args:
            ax: Matplotlib axes object
            y_values: List of y-coordinates for labels
            label_info: List of tuples (label_text, color)
            position: Where to place labels ('right', 'left', 'center')
            offset: Horizontal offset from edge as fraction of plot width
            fontsize: Font size for labels
            add_bbox: Whether to add background box to labels
        """
        # Get the current axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        # Calculate x position based on desired alignment
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]

        if position == "right":
            x_pos = xlim[1] - (offset * x_range)
            ha = "right"
        elif position == "left":
            x_pos = xlim[0] + (offset * x_range)
            ha = "left"
        else:  # center
            x_pos = xlim[0] + 0.5 * x_range
            ha = "center"

        # Sort labels by y-value to handle overlapping
        sorted_labels = sorted(zip(y_values, label_info, strict=False), key=lambda x: x[0])

        # Adjust y-positions to prevent overlap
        adjusted_positions = self._adjust_label_positions(
            [y for y, _ in sorted_labels],
            y_range * 0.02,  # 2% of plot height minimum spacing
        )

        # Add each label
        for _i, ((y_val, (label_text, color)), adj_y) in enumerate(
            zip(sorted_labels, adjusted_positions, strict=False)
        ):
            # Create bbox styling if requested
            bbox_props = None
            if add_bbox:
                bbox_props = dict(
                    boxstyle="round,pad=0.2",
                    facecolor="white",
                    edgecolor=color,
                    alpha=0.8,
                    linewidth=1,
                )

            # Add the text label
            ax.text(
                x_pos,
                adj_y,
                label_text,
                fontsize=fontsize,
                ha=ha,
                va="center",
                color=color,
                fontweight="bold",
                bbox=bbox_props,
                zorder=10,  # Make sure labels appear on top
            )

            # If we adjusted the position, draw a small line connecting to the actual line
            if abs(adj_y - y_val) > y_range * 0.01:  # Only if significantly moved
                # Draw a thin connecting line
                connect_x = x_pos + (0.01 * x_range if ha == "right" else -0.01 * x_range)
                ax.plot(
                    [connect_x, x_pos],
                    [y_val, adj_y],
                    color=color,
                    linewidth=1,
                    alpha=0.5,
                    zorder=5,
                )

    def _adjust_label_positions(self, y_positions, min_spacing):
        """
        Adjust label positions to prevent overlapping.

        Args:
            y_positions: List of original y-positions (sorted)
            min_spacing: Minimum spacing between labels

        Returns:
            List of adjusted y-positions
        """
        if len(y_positions) <= 1:
            return y_positions

        adjusted = [y_positions[0]]  # First position stays the same

        for i in range(1, len(y_positions)):
            current_y = y_positions[i]
            prev_adjusted = adjusted[i - 1]

            # If too close to previous label, push it up
            if current_y - prev_adjusted < min_spacing:
                adjusted.append(prev_adjusted + min_spacing)
            else:
                adjusted.append(current_y)

        return adjusted

    def _get_text_bbox_display(self, text, fontsize, color, add_bbox, renderer, ax):
        """Creates a temporary text object and returns its bounding box in display coordinates (pixels)."""
        if renderer is None:
            return None

        bbox_props = None
        if add_bbox:
            # Define the style for the bounding box
            bbox_props = dict(
                boxstyle="round,pad=0.2", facecolor="white", edgecolor=color, alpha=0.8, linewidth=1
            )

        # Create a temporary, invisible text object on the axes to measure it
        # We must attach it to the axes to inherit the correct styles and renderer context.
        temp_text = ax.text(
            0, 0, text, fontsize=fontsize, fontweight="bold", bbox=bbox_props, visible=False
        )

        try:
            # Get the bounding box in display coordinates using the renderer
            # This accurately measures the text including font rendering and bbox padding.
            bbox = temp_text.get_window_extent(renderer=renderer)
        except Exception as e:
            logger.warning(f"Could not get window extent for label '{text}': {e}")
            bbox = None
        finally:
            # Clean up the temporary object
            temp_text.remove()

        return bbox

    def _add_direct_line_endpoint_labels(
        self, ax, x_data, y_data, labels, colors, style, fig=None, **kwargs
    ):
        """
        Add labels directly on chart near line endpoints. Uses display coordinates for robust placement.
        """
        # Extract configuration options
        config = kwargs.get("direct_line_labels", {})
        if not isinstance(config, dict):
            config = {}

        position_mode = config.get("position", "auto")
        add_bbox = config.get("bbox", True)
        fontsize = config.get("fontsize", style.get("legend_size", 12))
        end_point_config = config.get("end_point", False)
        # Retrieve markersize passed down from _create_chart
        markersize_points = kwargs.get("markersize", style.get("marker_size", 6))

        # Parse end_point config - can be:
        # - False: no endpoints
        # - True: default endpoints for all series
        # - dict: same custom style for all series
        # - list: per-series styles (each element can be False, True, or dict)
        end_point_configs = None
        end_point_default_opts = {}
        if isinstance(end_point_config, list):
            # Per-series configuration
            end_point_configs = end_point_config
        elif isinstance(end_point_config, dict):
            # Same style for all series
            end_point_configs = "all_same"
            end_point_default_opts = end_point_config
        elif end_point_config:
            # True - default style for all series
            end_point_configs = "all_same"

        if fig is None:
            return

        renderer = None
        try:
            # Renderer should be available because we called fig.canvas.draw() in _apply_axes_styling
            renderer = fig.canvas.get_renderer()
        except Exception as e:
            logger.warning(f"Renderer not available for direct labeling: {e}")
            # If auto mode relies on the renderer, we must exit if it's not available.
            if position_mode == "auto":
                return

        # Handle X data conversion (Categorical to Numeric Indices for transformations)
        if x_data is None:
            if y_data and len(y_data) > 0 and len(y_data[0]) > 0:
                numeric_x = np.arange(len(y_data[0]))
            else:
                return
        # Check if the first element of x_data is a string
        elif len(x_data) > 0 and isinstance(next(iter(x_data)), str):
            numeric_x = np.arange(len(x_data))
        else:
            # Attempt conversion to numpy array for consistency
            try:
                numeric_x = np.array(x_data)
            except Exception as e:
                logger.error(f"Could not process x_data for direct labeling: {e}")
                return

        # Prepare line data in display coordinates for collision detection (only if auto mode)
        all_line_data_display = []
        if position_mode == "auto" and renderer:
            for y_series in y_data:
                points = []
                # Ensure y_series is iterable
                y_series_list = list(y_series)

                # Iterate through the data points
                min_len = min(len(numeric_x), len(y_series_list))
                for i in range(min_len):
                    x = numeric_x[i]
                    y = y_series_list[i]
                    if x is not None and y is not None:
                        try:
                            # Ensure numeric and finite values before transformation
                            x_val, y_val = float(x), float(y)
                            if np.isfinite(x_val) and np.isfinite(y_val):
                                points.append((x_val, y_val))
                        except (TypeError, ValueError):
                            continue

                if points:
                    # Transform the entire line path to pixels
                    pixels = ax.transData.transform(points)
                    all_line_data_display.append(pixels)

        # Collect endpoint information and find optimal positions
        existing_labels_bboxes = []  # List of Bbox objects in display coordinates

        for _i, (y_series, label_text, color) in enumerate(
            zip(y_data, labels, colors, strict=False)
        ):
            # Skip series with None labels
            if label_text is None:
                continue

            # Find the last non-None/finite point in the series
            last_x_idx = -1
            last_y = None
            y_series_list = list(y_series)

            # Iterate backwards to find the last valid point
            for idx in range(len(y_series_list) - 1, -1, -1):
                y_val = y_series_list[idx]
                # Check if the corresponding x value is also valid
                if idx < len(numeric_x) and numeric_x[idx] is not None and y_val is not None:
                    try:
                        # Check finiteness if numeric
                        y_val_float = float(y_val)
                        if np.isfinite(y_val_float):
                            last_x_idx = idx
                            last_y = y_val_float
                            break
                    except (TypeError, ValueError):
                        continue

            if last_x_idx == -1:
                continue

            last_x = numeric_x[last_x_idx]

            # --- Placement Logic ---

            # 1. Get the bounding box of the text in display coordinates (if renderer available)
            text_bbox = self._get_text_bbox_display(
                label_text, fontsize, color, add_bbox, renderer, ax
            )

            # 2. Determine position
            # For 'auto' mode, we need the text_bbox for collision detection
            # For simple modes (right, left, etc.), we can place without bbox
            if position_mode == "auto":
                if text_bbox is None:
                    # Auto mode requires bbox for collision detection, skip this label
                    continue
                optimal_pos = self._find_optimal_label_position_display(
                    last_x,
                    last_y,
                    text_bbox,
                    all_line_data_display,
                    existing_labels_bboxes,
                    ax,
                    markersize_points,
                )
            else:
                # Simple position modes can work with or without text_bbox
                optimal_pos = self._get_simple_label_position(
                    last_x, last_y, text_bbox, position_mode, ax, markersize_points
                )

            # 3. Place the text and store the resulting bbox
            if optimal_pos:
                bbox_props = None
                if add_bbox:
                    bbox_props = dict(
                        boxstyle="round,pad=0.2",
                        facecolor="white",
                        edgecolor=color,
                        alpha=0.8,
                        linewidth=1,
                    )

                ax.text(
                    optimal_pos["x_data"],
                    optimal_pos["y_data"],
                    label_text,
                    fontsize=fontsize,
                    ha=optimal_pos["ha"],
                    va=optimal_pos["va"],
                    color=color,
                    fontweight="bold",
                    bbox=bbox_props,
                    zorder=10,
                )
                # Store the actual placed bbox for subsequent collision detection (if available)
                if optimal_pos["bbox_display"] is not None:
                    existing_labels_bboxes.append(optimal_pos["bbox_display"])

                # Draw endpoint marker if enabled
                # Determine endpoint config for this series
                show_this_endpoint = False
                this_endpoint_opts = {}

                if end_point_configs == "all_same":
                    show_this_endpoint = True
                    this_endpoint_opts = end_point_default_opts
                elif isinstance(end_point_configs, list) and _i < len(end_point_configs):
                    series_ep_config = end_point_configs[_i]
                    if isinstance(series_ep_config, dict):
                        show_this_endpoint = True
                        this_endpoint_opts = series_ep_config
                    elif series_ep_config:
                        show_this_endpoint = True

                if show_this_endpoint:
                    # Extract endpoint styling options with defaults
                    ep_marker = this_endpoint_opts.get("marker", "o")
                    ep_size = this_endpoint_opts.get("size", markersize_points)
                    ep_facecolor = this_endpoint_opts.get("facecolor", color)
                    ep_edgecolor = this_endpoint_opts.get("edgecolor", "white")
                    ep_edgewidth = this_endpoint_opts.get("edgewidth", 1.5)
                    ep_zorder = this_endpoint_opts.get("zorder", 9)

                    ax.plot(
                        last_x,
                        last_y,
                        marker=ep_marker,
                        markersize=ep_size,
                        color=color,
                        markerfacecolor=ep_facecolor,
                        markeredgecolor=ep_edgecolor,
                        markeredgewidth=ep_edgewidth,
                        linestyle="None",
                        zorder=ep_zorder,
                    )

    def _get_simple_label_position(
        self, x_data, y_data, text_bbox, position_mode, ax, markersize_points
    ):
        """Calculates position for simple modes using point offsets (DPI-aware)."""
        # Define offset in points (marker radius + desired gap)
        gap_points = 8  # Increased gap for better visual separation
        minimum_offset_points = 12  # Ensure minimum distance from endpoint
        offset_points = max((markersize_points / 2.0) + gap_points, minimum_offset_points)

        # Determine offset and alignment based on position mode
        # offset_copy creates a transform with the offset built-in (cannot be modified after)
        if position_mode == "right":
            x_offset, y_offset = offset_points, 0
            ha, va = "left", "center"
        elif position_mode == "left":
            x_offset, y_offset = -offset_points, 0
            ha, va = "right", "center"
        elif position_mode == "above" or position_mode == "top":
            x_offset, y_offset = 0, offset_points
            ha, va = "center", "bottom"
        elif position_mode == "below" or position_mode == "bottom":
            x_offset, y_offset = 0, -offset_points
            ha, va = "center", "top"
        else:
            # Default fallback to right
            x_offset, y_offset = offset_points, 0
            ha, va = "left", "center"

        # Convert datetime to matplotlib date numbers for proper transform round-trip
        # numpy datetime64 nanoseconds don't survive the transform -> inverted transform cycle
        x_for_transform = x_data
        if hasattr(x_data, "dtype") and np.issubdtype(x_data.dtype, np.datetime64):
            x_for_transform = mdates.date2num(x_data)

        # Use offset_copy to create a transformation that shifts by points
        # This is DPI-aware and handled by Matplotlib.
        transform = matplotlib.transforms.offset_copy(
            ax.transData, fig=ax.get_figure(), x=x_offset, y=y_offset, units="points"
        )

        # Calculate anchor location in display coords
        anchor_display = transform.transform((x_for_transform, y_data))
        # Transform back to data coordinates for ax.text()
        anchor_data = ax.transData.inverted().transform(anchor_display)

        # The final x coordinate to use for ax.text()
        # matplotlib's date numbers (days since epoch) work directly with ax.text
        final_x = anchor_data[0]

        # Calculate the final bounding box in display coordinates for collision tracking
        # (only if text_bbox is available)
        final_bbox = None
        if text_bbox is not None:
            width, height = text_bbox.width, text_bbox.height
            x0, y0 = anchor_display[0], anchor_display[1]

            # Determine the starting corner (x_start, y_start) based on alignment
            if ha == "left":
                x_start = x0
            elif ha == "right":
                x_start = x0 - width
            else:  # center
                x_start = x0 - width / 2

            # Display coordinates (0,0) at bottom-left.
            if va == "bottom":
                y_start = y0
            elif va == "top":
                y_start = y0 - height
            else:  # center
                y_start = y0 - height / 2

            final_bbox = Bbox.from_bounds(x_start, y_start, width, height)

        return {
            "x_data": final_x,
            "y_data": anchor_data[1],
            "ha": ha,
            "va": va,
            "bbox_display": final_bbox,
        }

    def _find_optimal_label_position_display(
        self,
        x_data,
        y_data,
        text_bbox,
        all_line_data_display,
        existing_labels_bboxes,
        ax,
        markersize_points,
    ):
        """
        Finds the optimal label position using a clockwise search strategy in display coordinates.
        """
        # 1. Get endpoint in pixels
        try:
            endpoint_px = ax.transData.transform([(x_data, y_data)])[0]
            ep_x_px, ep_y_px = endpoint_px[0], endpoint_px[1]
        except Exception as e:
            logger.error(f"Error transforming endpoint coordinates: {e}")
            return None

        # 2. Define Offsets in Pixels (DPI-Aware)
        dpi = ax.get_figure().get_dpi()

        # Gap heuristic: 8 points (increased for better visual separation)
        gap_points = 8
        minimum_offset_points = 12  # Ensure minimum distance from endpoint

        # Total distance from center = max of (marker radius + gap) or minimum offset
        offset_points = max((markersize_points / 2.0) + gap_points, minimum_offset_points)
        offset_px = offset_points * (dpi / 72.0)  # Convert points to pixels

        text_width_px = text_bbox.width
        text_height_px = text_bbox.height

        # 3. Get Axes bounds in pixels
        # We rely on the renderer being initialized (canvas drawn) before this function is called.
        renderer = ax.get_figure().canvas.get_renderer()

        # get_window_extent provides the bounds of the plotting area.
        ax_bbox = ax.get_window_extent(renderer=renderer)

        # 4. Search Strategy: Clockwise starting from Right (0 degrees)
        # Define 8 cardinal directions. Angles are standard mathematical (CCW from right).
        # (Angle, HA, VA) - Ordered by preference.
        priority_directions = [
            (0, "left", "center"),  # Right (Preferred)
            (315, "left", "top"),  # Bottom-Right
            (270, "center", "top"),  # Bottom
            (225, "right", "top"),  # Bottom-Left
            (180, "right", "center"),  # Left
            (135, "right", "bottom"),  # Top-Left
            (90, "center", "bottom"),  # Top
            (45, "left", "bottom"),  # Top-Right
        ]

        best_position = None
        best_score = float("inf")

        # Iterate through the directions in order of preference.
        for pref_order, (angle_deg, ha, va) in enumerate(priority_directions):
            angle_rad = math.radians(angle_deg)

            # Calculate the anchor position coordinates
            anchor_x_px = ep_x_px + offset_px * math.cos(angle_rad)
            anchor_y_px = ep_y_px + offset_px * math.sin(angle_rad)

            # Calculate the full bounding box (in pixels) of the label at this position
            # Determine the bottom-left corner (bbox_x1, bbox_y1) based on alignment
            if ha == "left":
                bbox_x1 = anchor_x_px
            elif ha == "right":
                bbox_x1 = anchor_x_px - text_width_px
            else:  # center
                bbox_x1 = anchor_x_px - text_width_px / 2

            # Display coordinates (0,0) at bottom-left.
            if va == "bottom":
                bbox_y1 = anchor_y_px
            elif va == "top":
                bbox_y1 = anchor_y_px - text_height_px
            else:  # center
                bbox_y1 = anchor_y_px - text_height_px / 2

            bbox_x2 = bbox_x1 + text_width_px
            bbox_y2 = bbox_y1 + text_height_px

            # Create a Bbox object
            label_bbox = Bbox.from_extents(bbox_x1, bbox_y1, bbox_x2, bbox_y2)

            # Score this position
            score = self._score_label_position_display(
                label_bbox, pref_order, all_line_data_display, existing_labels_bboxes, ax_bbox
            )

            # Track best position
            if score < best_score:
                best_score = score
                # Convert best pixel coordinates back to data coordinates for placement
                anchor_data = ax.transData.inverted().transform([(anchor_x_px, anchor_y_px)])[0]
                best_position = {
                    "x_data": anchor_data[0],
                    "y_data": anchor_data[1],
                    "ha": ha,
                    "va": va,
                    "score": score,
                    "bbox_display": label_bbox,
                }

            # Early exit if score is perfect (0) - means it's the preferred spot (Right) and has no collisions.
            if score == 0:
                break

        # Fallback if optimization fails completely (e.g. endpoint is off-screen or area is too crowded)
        if best_position is None:
            logger.warning(
                "Could not find an optimal position for the label. Falling back to 'right'."
            )
            return self._get_simple_label_position(
                x_data, y_data, text_bbox, "right", ax, markersize_points
            )

        return best_position

    def _score_label_position_display(
        self, label_bbox, pref_order, all_line_data_display, existing_labels_bboxes, ax_bbox
    ):
        """Scores the label position in pixel coordinates. Lower is better."""
        score = 0

        # 1. Penalty based on preference order (Clockwise from Right)
        # pref_order starts at 0 for 'Right'. This enforces the priority.
        score += pref_order * 5

        # 2. Heavy penalty for going outside axes bounds.
        # Use a small padding (e.g., 5 pixels) from the edge of the axes.
        padding = 5
        if (
            label_bbox.x0 < ax_bbox.x0 + padding
            or label_bbox.x1 > ax_bbox.x1 - padding
            or label_bbox.y0 < ax_bbox.y0 + padding
            or label_bbox.y1 > ax_bbox.y1 - padding
        ):
            score += 200

        # 3. Penalty for overlapping with existing labels.
        # Add a small buffer between labels (e.g. 4 pixels)
        buffer = 4

        # Expand the bbox slightly for the overlap check to enforce the buffer
        try:
            buffered_bbox = label_bbox.expanded(
                1 + buffer / label_bbox.width, 1 + buffer / label_bbox.height
            )
        except ZeroDivisionError:
            buffered_bbox = label_bbox  # Handle case where bbox might have zero width/height

        for existing_bbox in existing_labels_bboxes:
            if buffered_bbox.overlaps(existing_bbox):
                score += 100

        # 4. Penalty for overlapping with line segments.
        if self._label_intersects_line_display(label_bbox, all_line_data_display):
            score += 50

        return score

    def _label_intersects_line_display(self, bbox, all_line_data_display):
        """Checks if the bounding box intersects any lines using pixel coordinates and Path intersection."""

        # Define the bounding box as a Path
        try:
            # Use bbox.corners() which returns the vertices of the rectangle.
            # closed=True ensures it's treated as a polygon.
            bbox_path = mpath.Path(bbox.corners(), closed=True)
        except Exception as e:
            logger.warning(f"Could not create bbox path for intersection check: {e}")
            return False

        for line_pixels in all_line_data_display:
            if len(line_pixels) < 2:
                continue

            try:
                # Create a Path for the line
                line_path = mpath.Path(line_pixels)

                # Check if the line path intersects the interior of the bounding box
                # filled=True treats bbox_path as a filled area, which is robust for detection.
                if bbox_path.intersects_path(line_path, filled=True):
                    return True

                # Also explicitly check if any line points are inside the bbox
                if bbox.contains_points(line_pixels).any():
                    return True

            except Exception as e:
                logger.debug(f"Line path intersection check failed: {e}")

        return False
