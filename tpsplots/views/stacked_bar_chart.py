"""Stacked bar chart visualization specialized view."""

import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .chart_view import ChartView
from .mixins import BarChartMixin, ColorCycleMixin, GridAxisMixin

logger = logging.getLogger(__name__)


class StackedBarChartView(BarChartMixin, ColorCycleMixin, GridAxisMixin, ChartView):
    """Specialized view for stacked bar charts with a focus on exposing matplotlib's API."""

    def stacked_bar_plot(self, metadata, stem, **kwargs):
        """
        Generate stacked bar charts for both desktop and mobile.

        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments passed directly to matplotlib's plotting functions.
            Required parameters:
            - categories: list/array - Category labels for x-axis or y-axis
            - values: dict or DataFrame - Values for each stack segment
                     Can be a dict like {'Category A': [10, 20, 30], 'Category B': [15, 25, 35]}
                     or a DataFrame with categories as index and stack segments as columns

            Optional parameters:
            - labels: list - Labels for each stack segment (legend items)
            - colors: list - Colors for each stack segment
            - orientation: str - 'vertical' (default) or 'horizontal'
            - show_values: bool - Whether to show values within each stack segment (default: False)
            - value_format: str - Format for values: presets ('monetary', 'percentage', 'integer', 'float') or Python format spec (e.g., '.1f', '.2f', ',.0f')
            - value_suffix: str - Optional text to append to formatted segment values (e.g., ' yrs', default: '')
            - value_threshold: float - Minimum percentage of total to show value label (default: 5.0)
            - value_fontsize: int - Font size for value labels (default: from style)
            - value_color: str - Color for value text (default: 'white')
            - value_weight: str - Font weight for values ('normal', 'bold', default: 'bold')
            - stack_labels: bool - Whether to show total values at end of each bar (default: False)
            - stack_label_format: str - Format for stack total labels: presets ('monetary', 'percentage', 'integer', 'float') or Python format spec (e.g., '.1f', '.2f', ',.0f')
            - stack_label_suffix: str - Optional text to append to stack total labels (default: value_suffix)
            - width: float - Width of bars for vertical charts (default: 0.8)
            - height: float - Height of bars for horizontal charts (default: 0.8)
            - bottom_values: list - Custom bottom values for stacking (advanced use)
            - alpha: float - Transparency (default: 1.0)
            - edgecolor: str - Edge color for bars (default: 'white')
            - linewidth: float - Edge line width (default: 0.5)
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - xlim: tuple/dict - X-axis limits
            - ylim: tuple/dict - Y-axis limits
            - xlabel: str - X-axis label
            - ylabel: str - Y-axis label
            - legend: bool/dict - Legend display and parameters
            - grid: bool - Show grid (default: True)
            - grid_axis: str - Grid axis ('x', 'y', 'both', default: based on orientation)
            - show_category_ticks: bool - Show tick marks on category axis (default: False)

        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a stacked bar chart with appropriate styling.

        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for chart creation

        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        categories = kwargs.pop("categories", None)
        values = kwargs.pop("values", None)

        if categories is None or values is None:
            raise ValueError("Both 'categories' and 'values' are required for stacked_bar_plot")

        # Parse literal newline sequences in category labels to actual newlines
        categories = self._parse_newlines_in_labels(categories)

        # Convert values to DataFrame if it's a dict
        if isinstance(values, dict):
            df = pd.DataFrame(values, index=categories)
        elif isinstance(values, pd.DataFrame):
            df = values.copy()
            if df.index.tolist() != list(categories):
                df.index = categories
        else:
            raise ValueError("'values' must be a dict or DataFrame")

        # Set up figure and extract metadata using base class helpers
        fig, ax = self._setup_figure(style, kwargs)
        self._extract_metadata_from_kwargs(metadata, kwargs)

        # Extract styling parameters
        orientation = kwargs.pop("orientation", "vertical")
        labels = kwargs.pop("labels", df.columns.tolist())
        colors = kwargs.pop("colors", None)
        show_values = kwargs.pop("show_values", False)
        value_format = kwargs.pop("value_format", "integer")
        value_suffix = kwargs.pop("value_suffix", "")
        value_threshold = kwargs.pop("value_threshold", 5.0)
        value_fontsize = kwargs.pop("value_fontsize", style.get("tick_size", 12) * 0.8)
        value_color = kwargs.pop("value_color", "white")
        value_weight = kwargs.pop("value_weight", "bold")
        stack_labels = kwargs.pop("stack_labels", False)
        stack_label_format = kwargs.pop("stack_label_format", value_format)
        stack_label_suffix = kwargs.pop("stack_label_suffix", value_suffix)
        width = kwargs.pop("width", 0.8)
        height = kwargs.pop("height", 0.8)
        alpha = kwargs.pop("alpha", 1.0)
        edgecolor = kwargs.pop("edgecolor", "white")
        linewidth = kwargs.pop("linewidth", 0.5)

        # Get colors (cycling through defaults if not provided or list is too short)
        colors = self._get_cycled_colors(len(df.columns), colors=colors)

        # Create the stacked bar chart
        bottom_values = kwargs.pop("bottom_values", None)

        if orientation == "vertical":
            self._create_vertical_stacked_bars(
                ax, df, colors, width, alpha, edgecolor, linewidth, bottom_values
            )
            x_positions = np.arange(len(categories))
            ax.set_xticks(x_positions)
            ax.set_xticklabels(categories)
        else:  # horizontal
            self._create_horizontal_stacked_bars(
                ax, df, colors, height, alpha, edgecolor, linewidth, bottom_values
            )
            y_positions = np.arange(len(categories))
            ax.set_yticks(y_positions)
            ax.set_yticklabels(categories)

        # Add value labels within stack segments if requested
        if show_values:
            self._add_value_labels(
                ax,
                df,
                orientation,
                value_format,
                value_suffix,
                value_threshold,
                value_fontsize,
                value_color,
                value_weight,
                width,
                height,
            )

        # Add stack total labels if requested
        if stack_labels:
            self._add_stack_labels(
                ax,
                df,
                orientation,
                stack_label_format,
                stack_label_suffix,
                value_fontsize,
                value_color,
                width,
                height,
            )

        # Apply styling
        self._apply_stacked_bar_styling(ax, style, orientation, **kwargs)

        # Add legend
        legend = kwargs.pop("legend", True)
        if legend and labels:
            # Create legend patches
            legend_patches = [
                plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor=edgecolor)
                for color in colors[: len(labels)]
            ]

            legend_kwargs = {"fontsize": style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)

            ax.legend(legend_patches, labels, **legend_kwargs)

        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)

        return fig

    def _create_vertical_stacked_bars(
        self, ax, df, colors, width, alpha, edgecolor, linewidth, bottom_values
    ):
        """Create vertical stacked bars."""
        x_positions = np.arange(len(df.index))

        if bottom_values is None:
            bottom_values = np.zeros(len(df.index))
        else:
            bottom_values = np.array(bottom_values)

        for i, column in enumerate(df.columns):
            values = df[column].values
            ax.bar(
                x_positions,
                values,
                width,
                bottom=bottom_values,
                color=colors[i],
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
                label=column,
            )
            bottom_values += values

    def _create_horizontal_stacked_bars(
        self, ax, df, colors, height, alpha, edgecolor, linewidth, bottom_values
    ):
        """Create horizontal stacked bars."""
        y_positions = np.arange(len(df.index))

        if bottom_values is None:
            bottom_values = np.zeros(len(df.index))
        else:
            bottom_values = np.array(bottom_values)

        for i, column in enumerate(df.columns):
            values = df[column].values
            ax.barh(
                y_positions,
                values,
                height,
                left=bottom_values,
                color=colors[i],
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
                label=column,
            )
            bottom_values += values

    def _add_value_labels(
        self,
        ax,
        df,
        orientation,
        value_format,
        value_suffix,
        threshold,
        fontsize,
        color,
        weight,
        width,
        height,
    ):
        """Add value labels within each stack segment."""
        positions = np.arange(len(df.index))

        # Calculate percentages for threshold filtering
        totals = df.sum(axis=1)

        if orientation == "vertical":
            bottom_values = np.zeros(len(df.index))
            for _i, column in enumerate(df.columns):
                values = df[column].values

                for j, (value, total) in enumerate(zip(values, totals, strict=False)):
                    # Check if segment is large enough to show label
                    percentage = (value / total * 100) if total > 0 else 0
                    if percentage >= threshold and value > 0:
                        # Calculate position for label (middle of segment)
                        y_pos = bottom_values[j] + value / 2

                        # Format the value
                        formatted_value = self._format_value(value, value_format) + value_suffix

                        ax.text(
                            positions[j],
                            y_pos,
                            formatted_value,
                            ha="center",
                            va="center",
                            fontsize=fontsize,
                            color=color,
                            weight=weight,
                        )

                bottom_values += values

        else:  # horizontal
            left_values = np.zeros(len(df.index))
            for _i, column in enumerate(df.columns):
                values = df[column].values

                for j, (value, total) in enumerate(zip(values, totals, strict=False)):
                    # Check if segment is large enough to show label
                    percentage = (value / total * 100) if total > 0 else 0
                    if percentage >= threshold and value > 0:
                        # Calculate position for label (middle of segment)
                        x_pos = left_values[j] + value / 2

                        # Format the value
                        formatted_value = self._format_value(value, value_format) + value_suffix

                        ax.text(
                            x_pos,
                            positions[j],
                            formatted_value,
                            ha="center",
                            va="center",
                            fontsize=fontsize,
                            color=color,
                            weight=weight,
                        )

                left_values += values

    def _add_stack_labels(
        self, ax, df, orientation, label_format, label_suffix, fontsize, color, width, height
    ):
        """Add total value labels at the end of each stacked bar."""
        positions = np.arange(len(df.index))
        totals = df.sum(axis=1)

        if orientation == "vertical":
            for i, total in enumerate(totals):
                formatted_total = self._format_value(total, label_format) + label_suffix
                ax.text(
                    positions[i],
                    total,
                    formatted_total,
                    ha="center",
                    va="bottom",
                    fontsize=fontsize,
                    color=self.COLORS["dark_gray"],
                    weight="bold",
                )
        else:  # horizontal
            for i, total in enumerate(totals):
                formatted_total = self._format_value(total, label_format) + label_suffix
                ax.text(
                    total,
                    positions[i],
                    formatted_total,
                    ha="left",
                    va="center",
                    fontsize=fontsize,
                    color=self.COLORS["dark_gray"],
                    weight="bold",
                )

    def _format_value(self, value, format_type):
        """
        Format values for stacked bar charts.

        Extends base class to skip zero values (common in stacked bars
        where segments may be empty).
        """
        # Skip zero values for cleaner stacked bar displays
        if value == 0:
            return ""
        # Delegate to base class for all other formatting
        return super()._format_value(value, format_type)

    # NOTE: _format_monetary is inherited from ChartView base class

    def _apply_stacked_bar_styling(self, ax, style, orientation, **kwargs):
        """Apply consistent styling to the stacked bar chart."""
        # Extract styling parameters
        scale = kwargs.pop("scale", None)
        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        grid = kwargs.pop("grid", True)
        grid_axis = kwargs.pop("grid_axis", "y" if orientation == "vertical" else "x")
        tick_size = kwargs.pop("tick_size", style.get("tick_size", 12))

        # Auto-rotation logic for category labels
        if orientation == "vertical":
            # Get current axis limits to calculate available width
            xlim_current = ax.get_xlim()
            chart_width = xlim_current[1] - xlim_current[0]
            num_categories = len(ax.get_xticklabels())

            if num_categories > 0:
                available_width_per_bar = chart_width / num_categories
                categories = [label.get_text() for label in ax.get_xticklabels()]

                # Determine if labels should be rotated
                should_rotate = self._should_rotate_labels(
                    ax, categories, tick_size, available_width_per_bar
                )
                tick_rotation = 90 if should_rotate else 0
            else:
                tick_rotation = 0
        else:
            # For horizontal charts, don't rotate y-axis labels
            tick_rotation = 0

        # Allow manual override of tick rotation
        tick_rotation = kwargs.pop("tick_rotation", tick_rotation)
        show_category_ticks = kwargs.pop("show_category_ticks", False)

        # Apply axis labels using mixin
        label_size = style.get("label_size", 12)
        tick_size = self._scale_tick_size_for_mobile(tick_size, style["type"])

        self._apply_axis_labels(
            ax,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            style_type=style["type"],
            italic=False,
        )

        # Apply grid using mixin
        self._apply_grid(ax, grid=grid, grid_axis=grid_axis)

        # Disable minor ticks using mixin
        self._disable_minor_ticks(ax)

        # Set tick sizes and rotation
        ax.tick_params(axis="x", labelsize=tick_size, rotation=tick_rotation)
        ax.tick_params(axis="y", labelsize=tick_size)

        # Control category tick mark visibility using mixin
        if not show_category_ticks:
            self._hide_category_ticks(ax, orientation)

        # Ensure category labels are centered using BarChartMixin methods
        if orientation == "vertical":
            self._apply_vertical_category_alignment(ax, tick_rotation)
        else:
            self._apply_horizontal_category_alignment(ax)

        # Apply scale formatter if specified
        if scale:
            axis_to_scale = "y" if orientation == "vertical" else "x"
            self._apply_scale_formatter(ax, scale, axis=axis_to_scale)

        # Ensure integer-only ticks for count-based data using mixin
        self._apply_integer_locator(ax, orientation)

        # Apply custom limits using mixin
        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)

    def _measure_text_width(self, ax, text, fontsize):
        """Measure the rendered width of text in data coordinates."""
        temp_text = ax.text(0, 0, text, fontsize=fontsize, transform=ax.transData)
        try:
            bbox = temp_text.get_window_extent(renderer=ax.figure.canvas.get_renderer())
            bbox_data = bbox.transformed(ax.transData.inverted())
            return bbox_data.width
        finally:
            temp_text.remove()

    def _should_rotate_labels(self, ax, categories, tick_size, available_width_per_bar):
        """Determine if category labels should be rotated based on text width."""
        # Calculate 80% of available width as threshold
        width_threshold = available_width_per_bar * 0.8

        # Check if any label exceeds the threshold
        for category in categories:
            text_width = self._measure_text_width(ax, str(category), tick_size)
            if text_width > width_threshold:
                return True

        return False
