"""Grouped bar chart visualization with support for side-by-side bars and partial stacking."""

import logging

import matplotlib.pyplot as plt
import numpy as np

from tpsplots.models.charts.grouped_bar import GroupedBarChartConfig

from .chart_view import ChartView
from .mixins import BarChartMixin, GridAxisMixin

logger = logging.getLogger(__name__)


class GroupedBarChartView(BarChartMixin, GridAxisMixin, ChartView):
    """Specialized view for grouped bar charts with optional stacking on last group."""

    CONFIG_CLASS = GroupedBarChartConfig

    def grouped_bar_plot(self, metadata, stem, **kwargs):
        """
        Generate grouped bar charts for both desktop and mobile.

        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments for chart customization:

            Required parameters:
            - categories: list - Category labels for x-axis (e.g., ["2000s", "2010s", "2020s"])
            - groups: list[dict] - List of group configurations, each with:
                - label: str - Group label for legend
                - values: list - Values for each category
                - color: str - Primary color for this group
                - stacked_values: list (optional) - Additional values to stack on last category
                - stacked_color: str (optional) - Color for stacked portion

            Optional parameters (consistent with BarChartView):
            - width: float - Width of each bar (default: 0.35)
            - show_values: bool - Show value labels on bars (default: True)
            - value_format: str - Format for values: 'integer', 'float', 'monetary', 'percentage'
            - value_prefix: str - Text to prepend to formatted values (default: '')
            - value_suffix: str - Text to append to formatted values (default: '')
            - value_offset: float - Distance from bar end for value labels (default: auto)
            - value_fontsize: float - Font size for value labels
            - value_color: str - Color for value labels (default: 'black')
            - value_weight: str - Font weight for values ('normal', 'bold', default: 'normal')
            - alpha: float - Bar transparency (default: 1.0)
            - edgecolor: str - Bar edge color (default: 'white')
            - linewidth: float - Bar edge width (default: 0.5)
            - xlabel: str - X-axis label (default: '')
            - ylabel: str - Y-axis label (default: '')
            - xlim: tuple/dict - X-axis limits
            - ylim: tuple/dict - Y-axis limits
            - grid: bool - Show grid (default: False)
            - grid_axis: str - Grid axis ('x', 'y', 'both', default: 'y')
            - scale: str - Value formatting scale ('billions', 'millions', etc.)
            - tick_rotation: int - Category label rotation (default: 0)
            - tick_size: int - Tick label font size
            - show_yticks: bool - Show y-axis tick labels (default: False)
            - legend: dict - Legend configuration
            - labels: list - Legend labels for each group (overrides group label)
            - export_data: DataFrame - CSV export DataFrame
            - colors: str/list - Optional override colors for groups (cycled if shorter)

        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a grouped bar chart with appropriate styling.

        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for chart creation

        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        categories = kwargs.pop("categories", None)
        groups = kwargs.pop("groups", None)
        colors = kwargs.pop("colors", None)
        labels = kwargs.pop("labels", None)

        if categories is None or groups is None:
            raise ValueError("Both 'categories' and 'groups' are required for grouped_bar_plot")

        # Set up figure and extract metadata using base class helpers
        fig, ax = self._setup_figure(style, kwargs)
        self._extract_metadata_from_kwargs(metadata, kwargs)

        # Extract optional parameters - standardized with BarChartView
        # Support both 'width' (standard) and 'bar_width' (legacy) for backwards compatibility
        width = kwargs.pop("width", kwargs.pop("bar_width", 0.35))
        show_values = kwargs.pop("show_values", True)
        value_format = kwargs.pop("value_format", "integer")
        value_prefix = kwargs.pop("value_prefix", "")
        value_suffix = kwargs.pop("value_suffix", "")
        value_offset = kwargs.pop("value_offset", None)
        value_fontsize = kwargs.pop("value_fontsize", style.get("tick_size", 14) * 0.6)
        value_color = kwargs.pop("value_color", "black")
        value_weight = kwargs.pop("value_weight", "normal")
        alpha = kwargs.pop("alpha", 1.0)
        edgecolor = kwargs.pop("edgecolor", "white")
        linewidth = kwargs.pop("linewidth", 0.5)

        # Axis and styling parameters
        xlabel = kwargs.pop("xlabel", "")
        ylabel = kwargs.pop("ylabel", "")
        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        grid = kwargs.pop("grid", False)
        grid_axis = kwargs.pop("grid_axis", "y")
        scale = kwargs.pop("scale", None)
        x_tick_format, y_tick_format = self._pop_axis_tick_format_kwargs(kwargs)
        tick_rotation = kwargs.pop("tick_rotation", 0)
        tick_size = kwargs.pop("tick_size", style.get("tick_size", 14))
        show_yticks = kwargs.pop("show_yticks", False)
        legend_config = kwargs.pop("legend", {"loc": "upper left"})

        # Set up bar positions
        x = np.arange(len(categories))
        num_groups = len(groups)

        # Calculate offsets to center groups
        total_width = width * num_groups
        offsets = np.linspace(-total_width / 2 + width / 2, total_width / 2 - width / 2, num_groups)

        # Track legend handles
        legend_handles = []
        legend_labels = []

        # Calculate auto value offset if needed (before plotting to get correct axis scale)
        if value_offset is None:
            # Estimate y range from data for auto offset calculation
            all_values = []
            for group in groups:
                values = group.get("values", [])
                all_values.extend(values)
                stacked_values = group.get("stacked_values")
                if stacked_values:
                    for v, sv in zip(values[-len(stacked_values) :], stacked_values, strict=False):
                        all_values.append(v + sv)
            if all_values:
                value_range = max(all_values) - min(0, min(all_values))
                value_offset = value_range * 0.02
            else:
                value_offset = 1.5  # fallback

        # Default colors for groups (used when not specified)
        default_colors = [
            self.TPS_COLORS["Neptune Blue"],
            self.TPS_COLORS["Rocket Flame"],
            self.TPS_COLORS["Plasma Purple"],
            self.TPS_COLORS["Lunar Soil"],
        ]

        # Normalize optional colors parameter (string or list)
        if isinstance(colors, str):
            colors_list = [colors] * num_groups
        elif isinstance(colors, (list, tuple)):
            colors_list = list(colors)
        else:
            colors_list = None

        # Plot each group
        for i, group in enumerate(groups):
            label = group.get("label", f"Group {i + 1}")
            if isinstance(labels, (list, tuple)) and i < len(labels):
                label = labels[i]
            elif labels is not None and i == 0 and isinstance(labels, str):
                label = labels
            values = np.array(group.get("values", []))
            color = group.get("color")
            if color is None and colors_list:
                color = colors_list[i % len(colors_list)]
            if color is None:
                color = default_colors[i % len(default_colors)]
            # Resolve TPS color names to hex if needed
            if color in self.TPS_COLORS:
                color = self.TPS_COLORS[color]
            stacked_values = group.get("stacked_values")
            stacked_color = group.get("stacked_color")

            pos = x + offsets[i]

            # Handle mixed simple/stacked bars
            if stacked_values is not None:
                stacked_values = np.array(stacked_values)

                # Plot base values for all categories
                # For categories without stacking, just plot the values
                # For the last category (or any with stacking), plot base then stack
                simple_count = len(values) - len(stacked_values)

                if simple_count > 0:
                    # Plot simple bars (no stacking)
                    ax.bar(
                        pos[:simple_count],
                        values[:simple_count],
                        width,
                        color=color,
                        alpha=alpha,
                        edgecolor=edgecolor,
                        linewidth=linewidth,
                    )

                # Plot stacked bars
                stacked_start = simple_count
                for j, (base_val, stack_val) in enumerate(
                    zip(values[stacked_start:], stacked_values, strict=False)
                ):
                    idx = stacked_start + j
                    # Base bar
                    ax.bar(
                        pos[idx],
                        base_val,
                        width,
                        color=color,
                        alpha=alpha,
                        edgecolor=edgecolor,
                        linewidth=linewidth,
                        label=label if idx == stacked_start else None,
                    )
                    # Stacked portion
                    ax.bar(
                        pos[idx],
                        stack_val,
                        width,
                        bottom=base_val,
                        color=stacked_color or self._lighten_color(color),
                        alpha=alpha,
                        edgecolor=edgecolor,
                        linewidth=linewidth,
                    )

                # Add value labels
                if show_values:
                    # Simple bars
                    for j in range(simple_count):
                        formatted_value = (
                            value_prefix
                            + self._format_value(values[j], value_format)
                            + value_suffix
                        )
                        ax.text(
                            pos[j],
                            values[j] + value_offset,
                            formatted_value,
                            ha="center",
                            va="bottom",
                            fontsize=value_fontsize,
                            color=value_color,
                            weight=value_weight,
                        )
                    # Stacked bars (show total)
                    for j, (base_val, stack_val) in enumerate(
                        zip(values[stacked_start:], stacked_values, strict=False)
                    ):
                        total = base_val + stack_val
                        idx = stacked_start + j
                        formatted_value = (
                            value_prefix + self._format_value(total, value_format) + value_suffix
                        )
                        ax.text(
                            pos[idx],
                            total + value_offset,
                            formatted_value,
                            ha="center",
                            va="bottom",
                            fontsize=value_fontsize,
                            color=value_color,
                            weight=value_weight,
                        )
            else:
                # Simple bars for all categories
                ax.bar(
                    pos,
                    values,
                    width,
                    color=color,
                    alpha=alpha,
                    edgecolor=edgecolor,
                    linewidth=linewidth,
                    label=label,
                )

                if show_values:
                    for j, val in enumerate(values):
                        formatted_value = (
                            value_prefix + self._format_value(val, value_format) + value_suffix
                        )
                        ax.text(
                            pos[j],
                            val + value_offset,
                            formatted_value,
                            ha="center",
                            va="bottom",
                            fontsize=value_fontsize,
                            color=value_color,
                            weight=value_weight,
                        )

            # Track for legend
            legend_handles.append(plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor=edgecolor))
            legend_labels.append(label)

        # Customize axes
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=tick_size, rotation=tick_rotation)

        label_size = style.get("label_size", 20)
        self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=grid,
            grid_axis=grid_axis,
            xlim=xlim,
            ylim=ylim,
            scale_ticks_for_mobile=False,
        )

        scaled_y = False

        # Style the chart - y-axis ticks
        if not show_yticks:
            ax.set_yticks([])
            ax.spines["left"].set_visible(False)
        else:
            ax.tick_params(axis="y", labelsize=tick_size)
            # Apply scale formatter if specified
            if scale:
                self._apply_scale_formatter(ax, scale, axis="y", tick_format=y_tick_format)
                scaled_y = True

            self._apply_tick_format_specs(
                ax,
                x_tick_format=x_tick_format,
                y_tick_format=y_tick_format if not scaled_y else None,
                has_explicit_xticklabels=True,
            )

        # Add legend
        if legend_config:
            legend_kwargs = {"fontsize": style.get("tick_size", 14) * 0.8}
            if isinstance(legend_config, dict):
                legend_kwargs.update(legend_config)
            ax.legend(legend_handles, legend_labels, **legend_kwargs)

        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)

        return fig

    def _lighten_color(self, color, factor=0.4):
        """
        Lighten a color by blending it with white.

        Args:
            color: Hex color string (e.g., "#037CC2")
            factor: Amount to lighten (0=no change, 1=white)

        Returns:
            Lightened hex color string
        """
        if color.startswith("#"):
            color = color[1:]

        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)

            r = int(r + (255 - r) * factor)
            g = int(g + (255 - g) * factor)
            b = int(b + (255 - b) * factor)

            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return color
