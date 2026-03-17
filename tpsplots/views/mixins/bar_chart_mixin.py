"""Mixin providing shared functionality for bar chart views."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter


class BarChartMixin:
    """
    Mixin class providing shared utilities for bar chart views.

    This mixin provides common functionality for BarChartView, GroupedBarChartView,
    and StackedBarChartView including:
    - Color determination based on values or parameters
    - Value label formatting and positioning
    - Axis styling and tick formatting
    - Legend generation for positive/negative value charts

    Note: This mixin expects the including class to have access to:
    - self.TPS_COLORS: dict of TPS brand colors
    - self._format_value(value, format_type): method to format values
    """

    def _determine_bar_colors(self, values, colors, positive_color, negative_color):
        """
        Determine the color for each bar based on values and color parameters.

        Args:
            values: Array of bar values
            colors: Base colors (str or list)
            positive_color: Color for positive values (optional)
            negative_color: Color for negative values (optional)

        Returns:
            List of colors for each bar
        """
        num_bars = len(values)

        # If positive/negative colors are specified, use value-based coloring
        if positive_color or negative_color:
            bar_colors = []
            default_positive = positive_color or self.TPS_COLORS["Neptune Blue"]
            default_negative = negative_color or self.TPS_COLORS["Rocket Flame"]

            for value in values:
                if value >= 0:
                    bar_colors.append(default_positive)
                else:
                    bar_colors.append(default_negative)

            return bar_colors

        # Otherwise, use standard color assignment
        if colors is None:
            # Use default TPS color
            return [self.TPS_COLORS["Neptune Blue"]] * num_bars
        elif isinstance(colors, str):
            # Single color for all bars
            return [colors] * num_bars
        elif isinstance(colors, (list, tuple)):
            # List of colors - cycle through if needed
            return [colors[i % len(colors)] for i in range(num_bars)]
        else:
            # Fallback to default
            return [self.TPS_COLORS["Neptune Blue"]] * num_bars

    def _add_bar_value_labels(
        self,
        ax,
        bars,
        values,
        orientation,
        value_format,
        value_suffix,
        value_offset,
        fontsize,
        color,
        weight,
        baseline=0,
    ):
        """
        Add value labels to each bar.

        Args:
            ax: Matplotlib axes object
            bars: Collection of bar patches from ax.bar() or ax.barh()
            values: Array of bar values
            orientation: 'vertical' or 'horizontal'
            value_format: Format preset or Python format spec
            value_suffix: Text to append after value
            value_offset: Distance from bar end (None for auto)
            fontsize: Label font size
            color: Label text color
            weight: Font weight ('normal' or 'bold')
            baseline: Baseline value for bars (default: 0)
        """
        if value_offset is None:
            # Auto-calculate offset based on orientation and value range
            if orientation == "vertical":
                value_range = ax.get_ylim()[1] - ax.get_ylim()[0]
                value_offset = value_range * 0.02  # 2% of range
            else:
                value_range = ax.get_xlim()[1] - ax.get_xlim()[0]
                value_offset = value_range * 0.02

        for bar, value in zip(bars, values, strict=False):
            # Format the value
            formatted_value = self._format_value(value, value_format) + value_suffix

            if orientation == "vertical":
                # Position label above or below bar depending on value
                if value >= baseline:
                    label_y = bar.get_height() + value_offset
                    va = "bottom"
                else:
                    label_y = bar.get_height() - value_offset
                    va = "top"

                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    label_y,
                    formatted_value,
                    ha="center",
                    va=va,
                    fontsize=fontsize,
                    color=color,
                    weight=weight,
                )
            else:  # horizontal
                # Position label to the right or left of bar depending on value
                if value >= baseline:
                    label_x = bar.get_width() + value_offset
                    ha = "left"
                else:
                    label_x = bar.get_width() - value_offset
                    ha = "right"

                ax.text(
                    label_x,
                    bar.get_y() + bar.get_height() / 2,
                    formatted_value,
                    ha=ha,
                    va="center",
                    fontsize=fontsize,
                    color=color,
                    weight=weight,
                )

    def _add_value_based_legend(self, ax, values, positive_color, negative_color, style):
        """
        Add legend for positive/negative value colors.

        Args:
            ax: Matplotlib axes object
            values: Array of bar values
            positive_color: Color for positive values
            negative_color: Color for negative values
            style: Style dictionary with legend_size
        """
        legend_elements = []
        legend_labels = []

        has_positive = np.any(np.array(values) >= 0)
        has_negative = np.any(np.array(values) < 0)

        if has_positive and positive_color:
            legend_elements.append(
                plt.Rectangle((0, 0), 1, 1, facecolor=positive_color, edgecolor="white")
            )
            legend_labels.append("Positive")

        if has_negative and negative_color:
            legend_elements.append(
                plt.Rectangle((0, 0), 1, 1, facecolor=negative_color, edgecolor="white")
            )
            legend_labels.append("Negative")

        if legend_elements:
            ax.legend(
                legend_elements,
                legend_labels,
                loc="upper right",
                fontsize=style.get("legend_size", 12),
            )

    def _apply_percentage_tick_formatter(self, ax, orientation):
        """
        Apply percentage formatting to the appropriate axis ticks.

        Args:
            ax: Matplotlib axes object
            orientation: Chart orientation ('vertical' or 'horizontal')
        """

        def percentage_formatter(x, pos):
            """Format tick labels as percentages."""
            return f"{x:.0f}%" if x != 0 else "0%"

        if orientation == "vertical":
            # For vertical bars, format y-axis (value axis)
            ax.yaxis.set_major_formatter(FuncFormatter(percentage_formatter))
        else:
            # For horizontal bars, format x-axis (value axis)
            ax.xaxis.set_major_formatter(FuncFormatter(percentage_formatter))

    def _apply_vertical_category_alignment(self, ax, tick_rotation):
        """
        Apply proper alignment for vertical bar chart category labels.

        Args:
            ax: Matplotlib axes object
            tick_rotation: Rotation angle for tick labels
        """
        # For vertical bars, x-axis labels should be centered under bars
        positions = np.arange(len(ax.get_xticklabels()))
        ax.set_xticks(positions)

        # Adjust alignment based on rotation angle
        if abs(tick_rotation) == 90:
            ha = "center"
            va = "top"
        elif tick_rotation != 0:
            ha = "right"
            va = "top"
        else:
            ha = "center"
            va = "top"

        # Apply the alignment to all x-axis labels
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment(ha)
            tick.set_verticalalignment(va)

    def _apply_horizontal_category_alignment(self, ax):
        """
        Apply proper alignment for horizontal bar chart category labels.

        Args:
            ax: Matplotlib axes object
        """
        # For horizontal bars, y-axis labels should be centered next to bars
        positions = np.arange(len(ax.get_yticklabels()))
        ax.set_yticks(positions)
        # Keep y-labels right-aligned for horizontal bars
        for tick in ax.get_yticklabels():
            tick.set_verticalalignment("center")
            tick.set_horizontalalignment("right")
