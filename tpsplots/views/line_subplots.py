"""Line subplots visualization specialized view."""

import logging

import matplotlib.pyplot as plt
import numpy as np

from tpsplots.models.charts.line_subplots import LineSubplotsChartConfig

from .chart_view import ChartView
from .mixins import GridAxisMixin, LineSeriesMixin

logger = logging.getLogger(__name__)


class LineSubplotsView(LineSeriesMixin, GridAxisMixin, ChartView):
    """Specialized view for creating line plots in a grid of subplots."""

    CONFIG_CLASS = LineSubplotsChartConfig

    def line_subplots_plot(self, metadata, stem, **kwargs):
        """
        Generate line subplot charts for both desktop and mobile.

        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Required parameters:
            - subplot_data: list of dicts, each containing:
                - x: x-axis data
                - y: y-axis data (can be list for multiple lines)
                - title: subplot title
                - labels: list of labels for each line (optional)
                - colors: list of colors for each line (optional)
                - linestyles: list of line styles (optional)
                - markers: list of markers for each line (optional)
            - grid_shape: tuple (rows, cols) for subplot grid (optional, auto-calculated if not provided)

            Optional parameters (applied to all subplots):
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - axis_scale: str - Which axis to scale ('x', 'y', or 'both', default: 'y')
            - shared_x: bool - Share x-axis across subplots (default: True)
            - shared_y: bool - Share y-axis across subplots (default: True)
            - legend: bool/dict - Legend display and parameters
            - xlim: tuple - X-axis limits applied to all subplots
            - ylim: tuple - Y-axis limits applied to all subplots
            - fiscal_year_ticks: bool - Use fiscal year formatting (default: True)
            - max_xticks: int - Maximum number of x-axis ticks
            - tick_rotation: float - Rotation angle for tick labels
            - xlabel: str - X-axis label
            - ylabel: str - Y-axis label
            - subplot_title_size: float - Font size for subplot titles (optional, defaults to label_size)
            - grid: bool - Show grid
            - grid_axis: str - Which axes to show grid on ('x', 'y', 'both')

        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _plot_subplot_series(
        self,
        ax,
        plot_data,
        style,
        *,
        shared_legend=False,
        is_first_subplot=False,
    ):
        """Plot all series for one subplot and return shared legend handles/labels."""
        x = plot_data.get("x")
        y_series_list = self._coerce_series_list(plot_data.get("y"))
        labels = plot_data.get("labels", None)
        colors = plot_data.get("colors", None)
        linestyles = plot_data.get("linestyles", None)
        markers = plot_data.get("markers", None)

        if x is None or y_series_list is None:
            return [], []

        num_series = len(y_series_list)
        color_values = self._normalize_series_param(colors, num_series)
        linestyle_values = self._normalize_series_param(linestyles, num_series, default="-")
        marker_values = self._normalize_series_param(markers, num_series)

        shared_handles = []
        shared_labels = []

        for i, y_series in enumerate(y_series_list):
            if y_series is None:
                continue

            x_valid, y_valid = self._filter_valid_xy(x, y_series)
            if len(x_valid) == 0 or len(y_valid) == 0:
                continue

            plot_kwargs = {"linestyle": linestyle_values[i], "linewidth": style["line_width"]}
            if color_values[i] is not None:
                plot_kwargs["color"] = color_values[i]
            if marker_values[i] is not None:
                plot_kwargs["marker"] = marker_values[i]
                plot_kwargs["markersize"] = style.get("marker_size", 5)

            current_label = None
            if isinstance(labels, (list, tuple)) and i < len(labels):
                current_label = labels[i]
            elif labels is not None and i == 0:
                current_label = labels

            if (shared_legend and is_first_subplot and current_label) or (
                not shared_legend and current_label
            ):
                plot_kwargs["label"] = current_label

            line = ax.plot(x_valid, y_valid, **plot_kwargs)
            if shared_legend and is_first_subplot and current_label:
                shared_handles.extend(line)
                shared_labels.append(current_label)

        return shared_handles, shared_labels

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create line subplots with appropriate styling.

        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for subplot creation

        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        subplot_data = kwargs.pop("subplot_data", None)
        grid_shape = kwargs.pop("grid_shape", None)

        if subplot_data is None:
            raise ValueError("subplot_data is required for line_subplots")
        if grid_shape is None:
            # Auto-calculate grid shape based on number of subplots
            n_plots = len(subplot_data)
            cols = int(np.ceil(np.sqrt(n_plots)))
            rows = int(np.ceil(n_plots / cols))
            grid_shape = (rows, cols)

        # Extract figure parameters
        figsize = kwargs.pop("figsize", style["figsize"])
        dpi = kwargs.pop("dpi", style["dpi"])

        # Extract subplot parameters
        shared_x = kwargs.pop("shared_x", True)
        shared_y = kwargs.pop("shared_y", True)

        # Extract global parameters that apply to all subplots
        global_scale = kwargs.pop("scale", None)
        global_xlim = kwargs.pop("xlim", None)
        global_ylim = kwargs.pop("ylim", None)
        global_legend = kwargs.pop("legend", True)
        shared_legend = kwargs.pop("shared_legend", False)  # NEW: Control shared legend
        legend_position = kwargs.pop(
            "legend_position", (0.5, -0.05)
        )  # NEW: Position for shared legend
        subplot_title_size = kwargs.pop("subplot_title_size", None)

        # Keep remaining kwargs for passing to subplot styling
        styling_kwargs = kwargs.copy()

        # Create figure and subplots
        fig, axes = plt.subplots(
            grid_shape[0],
            grid_shape[1],
            figsize=figsize,
            dpi=dpi,
            sharex=shared_x,
            sharey=shared_y,
            squeeze=False,
        )

        # Flatten axes array for easier iteration
        axes_flat = axes.flatten()

        # Collect handles and labels for shared legend
        all_handles = []
        all_labels = []

        # Plot data in each subplot
        for idx, (ax, plot_data) in enumerate(
            zip(axes_flat[: len(subplot_data)], subplot_data, strict=False)
        ):
            subplot_title = plot_data.get("title", f"Subplot {idx + 1}")
            labels = plot_data.get("labels", None)
            subplot_handles, subplot_labels = self._plot_subplot_series(
                ax,
                plot_data,
                style,
                shared_legend=shared_legend,
                is_first_subplot=idx == 0,
            )
            if subplot_handles:
                all_handles.extend(subplot_handles)
            if subplot_labels:
                all_labels.extend(subplot_labels)

            # Set subplot title
            title_fontsize = (
                subplot_title_size if subplot_title_size is not None else style["label_size"]
            )
            ax.set_title(subplot_title, fontsize=title_fontsize, pad=10)

            # Apply styling to this subplot with all kwargs
            subplot_kwargs = styling_kwargs.copy()
            subplot_kwargs.update({"scale": global_scale, "xlim": global_xlim, "ylim": global_ylim})
            self._apply_subplot_styling(ax, style, **subplot_kwargs)

            # Add individual legend if requested and not using shared legend
            if global_legend and not shared_legend and labels is not None:
                legend_kwargs = {"fontsize": style["legend_size"] * 0.8}
                if isinstance(global_legend, dict):
                    legend_kwargs.update(global_legend)
                ax.legend(**legend_kwargs)

        # Hide any unused subplots
        for idx in range(len(subplot_data), len(axes_flat)):
            axes_flat[idx].set_visible(False)

        # Add shared legend if requested
        if shared_legend and global_legend and all_handles and all_labels:
            legend_kwargs = {
                "fontsize": style["legend_size"],
                "loc": "center",
                "bbox_to_anchor": legend_position,
                "ncol": len(all_labels),  # Horizontal layout by default
                "frameon": True,
            }

            # Allow customization of shared legend
            if isinstance(global_legend, dict):
                legend_kwargs.update(global_legend)

            fig.legend(all_handles, all_labels, **legend_kwargs)

        # Apply tight layout before header/footer adjustment
        plt.tight_layout()

        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)

        return fig

    def _apply_subplot_styling(self, ax, style, **kwargs):
        """
        Apply consistent styling to each subplot, matching LineChart functionality.

        Args:
            ax: Matplotlib axes object
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Additional styling parameters
        """
        # Extract parameters with defaults
        scale = kwargs.get("scale")
        axis_scale = kwargs.get("axis_scale", "y")
        xlim = kwargs.get("xlim")
        ylim = kwargs.get("ylim")
        xlabel = kwargs.get("xlabel")
        ylabel = kwargs.get("ylabel")
        grid = kwargs.get("grid", style.get("grid"))
        grid_axis = kwargs.get("grid_axis", style.get("grid_axis", "both"))
        tick_size = kwargs.get("tick_size", style["tick_size"] * 0.5)  # Scale smaller for subplots
        tick_rotation = kwargs.get("tick_rotation", style.get("tick_rotation", 0))
        xticks = kwargs.get("xticks")
        xticklabels = kwargs.get("xticklabels")
        max_xticks = kwargs.get("max_xticks", style.get("max_ticks"))
        fiscal_year_ticks = kwargs.get("fiscal_year_ticks", True)
        tick_format_kwargs = dict(kwargs)
        x_tick_format, y_tick_format = self._pop_axis_tick_format_kwargs(tick_format_kwargs)

        self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=style["label_size"] * 0.9,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=grid,
            grid_axis=grid_axis,
            grid_alpha=0.3,
            grid_linestyle="-",
            grid_linewidth=0.8,
            italic=False,
            scale_ticks_for_mobile=False,
        )

        # Get x-axis data for date detection
        lines = ax.get_lines()
        x_data = None
        if lines:
            x_data = lines[0].get_xdata()

        # Apply appropriate tick formatting
        if fiscal_year_ticks and x_data is not None and self._contains_dates(x_data):
            # Apply special FY formatting
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
        elif x_data is not None and self._contains_dates(x_data):
            # Standard date formatting
            import matplotlib.dates as mdates

            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
        else:
            # Standard tick formatting
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)

            # Set tick locators if needed
            if max_xticks:
                ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))

        scaled_x = False
        scaled_y = False

        # Apply scale formatter if specified
        if scale:
            if axis_scale == "both":
                self._apply_scale_formatter(ax, scale, axis="x", tick_format=x_tick_format)
                self._apply_scale_formatter(ax, scale, axis="y", tick_format=y_tick_format)
                scaled_x = True
                scaled_y = True
            elif axis_scale == "x":
                self._apply_scale_formatter(ax, scale, axis="x", tick_format=x_tick_format)
                scaled_x = True
            else:
                self._apply_scale_formatter(ax, scale, axis="y", tick_format=y_tick_format)
                scaled_y = True

        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)

        # Apply custom ticks
        if xticks is not None:
            ax.set_xticks(xticks)
            if xticklabels is not None:
                ax.set_xticklabels(xticklabels)
            elif all(isinstance(x, (int, float)) and float(x).is_integer() for x in xticks):
                ax.set_xticklabels([f"{int(x)}" for x in xticks])

        self._apply_tick_format_specs(
            ax,
            x_tick_format=x_tick_format if not scaled_x else None,
            y_tick_format=y_tick_format if not scaled_y else None,
            has_explicit_xticklabels=xticklabels is not None,
        )

        # Special rotation for mobile
        if style == self.MOBILE and tick_rotation == 0:
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
