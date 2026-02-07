"""Enhanced bar chart with automatic percentage formatting for y-axis ticks."""

import logging

import matplotlib.pyplot as plt
import numpy as np

from tpsplots.models.charts.bar import BarChartConfig

from .chart_view import ChartView
from .mixins import BarChartMixin, GridAxisMixin

logger = logging.getLogger(__name__)


class BarChartView(BarChartMixin, GridAxisMixin, ChartView):
    """Specialized view for standard bar charts with a focus on exposing matplotlib's API."""

    CONFIG_CLASS = BarChartConfig

    def bar_plot(self, metadata, stem, **kwargs):
        """
        Generate bar charts for both desktop and mobile.

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
            - values: list/array/Series - Values for each bar

            Optional parameters:
            - orientation: str - 'vertical' (default) or 'horizontal'
            - colors: str/list - Colors for bars (default: TPS Neptune Blue)
            - positive_color: str - Color for positive values (overrides colors for positive bars)
            - negative_color: str - Color for negative values (overrides colors for negative bars)
            - show_values: bool - Whether to show values on each bar (default: False)
            - value_format: str - Format for values: presets ('monetary', 'percentage', 'integer', 'float') or Python format spec (e.g., '.1f', '.2f', ',.0f')
            - value_suffix: str - Optional text to append to formatted values (e.g., ' yrs', ' months', default: '')
            - value_offset: float - Offset for value labels from bar end (default: auto)
            - value_fontsize: int - Font size for value labels (default: from style)
            - value_color: str - Color for value text (default: 'black')
            - value_weight: str - Font weight for values ('normal', 'bold', default: 'normal')
            - width: float - Width of bars for vertical charts (default: 0.8)
            - height: float - Height of bars for horizontal charts (default: 0.8)
            - alpha: float - Transparency (default: 1.0)
            - edgecolor: str - Edge color for bars (default: 'white')
            - linewidth: float - Edge line width (default: 0.5)
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - xlim: tuple/dict - X-axis limits
            - ylim: tuple/dict - Y-axis limits
            - xlabel: str - X-axis label
            - ylabel: str - Y-axis label
            - legend: bool/dict - Legend display and parameters (for positive/negative colors)
            - grid: bool - Show grid (default: True)
            - grid_axis: str - Grid axis ('x', 'y', 'both', default: based on orientation)
            - sort_by: str - Sort categories by 'value', 'category', or None (default: None)
            - sort_ascending: bool - Sort direction if sort_by is specified (default: True)
            - show_category_ticks: bool - Show tick marks on category axis (default: False)
            - baseline: float - Baseline value for bars (default: 0)

        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)

    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a bar chart with appropriate styling.

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
            raise ValueError("Both 'categories' and 'values' are required for bar_plot")

        # Convert to numpy arrays for easier handling
        categories = np.array(categories)
        values = np.array(values)

        # Check for fiscal year data BEFORE any processing that modifies the data
        # fiscal_year_ticks: None = auto-detect, True = force on, False = force off
        fiscal_year_ticks = kwargs.pop("fiscal_year_ticks", None)
        if fiscal_year_ticks is None:
            categories_are_fiscal_years = self._contains_dates(categories)
        else:
            categories_are_fiscal_years = bool(fiscal_year_ticks)

        # Store original categories for fiscal year range calculation
        self._original_categories = categories if categories_are_fiscal_years else None

        # Parse literal newline sequences in category labels to actual newlines
        # This must happen AFTER fiscal year detection since it converts to strings
        categories = self._parse_newlines_in_labels(categories)

        # Validate data lengths
        if len(categories) != len(values):
            raise ValueError("categories and values must have the same length")

        # Extract colors early so they can be sorted along with the data
        colors = kwargs.pop("colors", None)

        # Handle sorting if requested
        sort_by = kwargs.pop("sort_by", None)
        sort_ascending = kwargs.pop("sort_ascending", True)

        if sort_by:
            sorted_indices = self._get_sort_indices(categories, values, sort_by, sort_ascending)
            categories = categories[sorted_indices]
            values = values[sorted_indices]

            # Also reorder colors to maintain association with categories
            if colors and isinstance(colors, (list, tuple)):
                colors = [colors[i] for i in sorted_indices]

        # Set up figure and extract metadata using base class helpers
        fig, ax = self._setup_figure(style, kwargs)
        self._extract_metadata_from_kwargs(metadata, kwargs)

        # Extract styling parameters
        orientation = kwargs.pop("orientation", "vertical")
        # colors already extracted earlier (before sorting)
        positive_color = kwargs.pop("positive_color", None)
        negative_color = kwargs.pop("negative_color", None)
        show_values = kwargs.pop("show_values", False)
        value_format = kwargs.pop("value_format", "float")
        value_suffix = kwargs.pop("value_suffix", "")
        value_offset = kwargs.pop("value_offset", None)
        value_fontsize = kwargs.pop("value_fontsize", style.get("tick_size", 12) * 0.9)
        value_color = kwargs.pop("value_color", "black")
        value_weight = kwargs.pop("value_weight", "normal")
        width = kwargs.pop("width", 0.8)
        height = kwargs.pop("height", 0.8)
        alpha = kwargs.pop("alpha", 1.0)
        edgecolor = kwargs.pop("edgecolor", "white")
        linewidth = kwargs.pop("linewidth", 0.5)
        baseline = kwargs.pop("baseline", 0)

        # Determine colors for each bar
        bar_colors = self._determine_bar_colors(values, colors, positive_color, negative_color)

        # Create the bar chart
        if orientation == "vertical":
            positions = np.arange(len(categories))
            bars = ax.bar(
                positions,
                values,
                width,
                bottom=baseline,
                color=bar_colors,
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
            )
            ax.set_xticks(positions)
            if not categories_are_fiscal_years:
                ax.set_xticklabels(categories)
        else:  # horizontal
            positions = np.arange(len(categories))
            bars = ax.barh(
                positions,
                values,
                height,
                left=baseline,
                color=bar_colors,
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
            )
            ax.set_yticks(positions)
            if not categories_are_fiscal_years:
                ax.set_yticklabels(categories)

        # Add value labels if requested
        if show_values:
            self._add_bar_value_labels(
                ax,
                bars,
                values,
                orientation,
                value_format,
                value_suffix,
                value_offset,
                value_fontsize,
                value_color,
                value_weight,
                baseline,
            )

        # Apply styling (now includes percentage formatting)
        self._apply_bar_styling(
            ax, style, orientation, categories_are_fiscal_years, value_format=value_format, **kwargs
        )

        # Add legend if multiple colors are used and labels are provided
        legend = kwargs.pop("legend", False)
        if legend and (positive_color or negative_color):
            self._add_value_based_legend(ax, values, positive_color, negative_color, style)

        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)

        return fig

    def _get_sort_indices(
        self,
        categories: np.ndarray,
        values: np.ndarray,
        sort_by: str,
        ascending: bool = True,
    ) -> np.ndarray:
        """Get indices for sorting the data."""
        if sort_by == "value":
            sort_values = values
        elif sort_by == "category":
            sort_values = categories
        else:
            raise ValueError(f"sort_by must be 'value' or 'category', got {sort_by}")

        return np.argsort(sort_values) if ascending else np.argsort(sort_values)[::-1]

    # NOTE: _determine_bar_colors, _add_bar_value_labels, _add_value_based_legend,
    # _apply_percentage_tick_formatter, _apply_vertical_category_alignment, and
    # _apply_horizontal_category_alignment are inherited from BarChartMixin

    def _apply_bar_styling(self, ax, style, orientation, categories_are_fiscal_years, **kwargs):
        """Apply consistent styling to the bar chart."""
        # Extract styling parameters
        x_tick_format, y_tick_format = self._pop_axis_tick_format_kwargs(kwargs)
        scale = kwargs.pop("scale", None)
        xlim = kwargs.pop("xlim", None)
        ylim = kwargs.pop("ylim", None)
        xlabel = kwargs.pop("xlabel", None)
        ylabel = kwargs.pop("ylabel", None)
        grid = kwargs.pop("grid", True)
        grid_axis = kwargs.pop("grid_axis", "y" if orientation == "vertical" else "x")
        tick_size = kwargs.pop("tick_size", style.get("tick_size", 12))
        label_size = kwargs.pop("label_size", style.get("label_size", 20))

        # Calculate default rotation based on orientation
        # For horizontal bars, value axis (x-axis) should never be rotated
        # For vertical bars, category axis (x-axis) may need rotation for long labels
        default_rotation = style.get("tick_rotation", 45) if orientation == "vertical" else 0

        # Allow manual override via YAML parameter
        tick_rotation = kwargs.pop("tick_rotation", default_rotation)
        baseline = kwargs.pop("baseline", 0)
        value_format = kwargs.pop("value_format", None)  # Extract value_format
        show_category_ticks = kwargs.pop("show_category_ticks", False)

        tick_size = self._apply_common_axis_styling(
            ax,
            style=style,
            xlabel=xlabel,
            ylabel=ylabel,
            label_size=label_size,
            tick_size=tick_size,
            tick_rotation=tick_rotation,
            grid=grid,
            grid_axis=grid_axis,
            xlim=None,
            ylim=None,
            scale_ticks_for_mobile=True,
        )

        # Add baseline reference line if different from 0
        if baseline != 0:
            if orientation == "vertical":
                ax.axhline(y=baseline, color="gray", linestyle="-", linewidth=1, alpha=0.7)
            else:
                ax.axvline(x=baseline, color="gray", linestyle="-", linewidth=1, alpha=0.7)

        # Disable minor ticks using mixin method
        self._disable_minor_ticks(ax)

        scaled_x = False
        scaled_y = False

        # Apply percentage formatting if value_format is 'percentage'
        if value_format == "percentage":
            self._apply_percentage_tick_formatter(ax, orientation)
            scaled_y = orientation == "vertical"
            scaled_x = orientation == "horizontal"

        # Apply scale formatter if specified (but not if we already applied percentage formatting)
        elif scale:
            axis_to_scale = "y" if orientation == "vertical" else "x"
            tick_format = y_tick_format if axis_to_scale == "y" else x_tick_format
            self._apply_scale_formatter(ax, scale, axis=axis_to_scale, tick_format=tick_format)
            scaled_y = axis_to_scale == "y"
            scaled_x = axis_to_scale == "x"

        # Apply appropriate tick formatting based on fiscal year detection
        if categories_are_fiscal_years and orientation == "vertical":
            # Apply special FY formatting using the base class method
            # but with bar chart-specific xlim calculation
            self._apply_fiscal_year_bar_ticks(ax, style, tick_size=tick_size)
        else:
            # Set tick locators if needed
            max_xticks = kwargs.pop("max_xticks", style.get("max_ticks"))
            if max_xticks and orientation == "vertical":
                ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))

        self._apply_tick_format_specs(
            ax,
            x_tick_format=x_tick_format if not scaled_x else None,
            y_tick_format=y_tick_format if not scaled_y else None,
            has_explicit_xticklabels=orientation == "vertical",
            has_explicit_yticklabels=orientation == "horizontal",
        )

        # Ensure integer-only ticks on value axis using mixin method
        self._apply_integer_locator(ax, orientation=orientation)

        # Control category tick mark visibility using mixin method
        if not show_category_ticks:
            self._hide_category_ticks(ax, orientation=orientation)

        # Apply custom limits using mixin method
        self._apply_axis_limits(ax, xlim=xlim, ylim=ylim)

        # Apply category alignment for non-fiscal year cases or when needed
        if not categories_are_fiscal_years or orientation != "vertical":
            if orientation == "vertical":
                self._apply_vertical_category_alignment(ax, tick_rotation)
            else:
                self._apply_horizontal_category_alignment(ax)

    def _apply_fiscal_year_bar_ticks(self, ax, style, tick_size):
        """
        Apply fiscal year tick formatting specifically for bar charts.

        Unlike line charts which use continuous date axes, bar charts use
        categorical positioning (0, 1, 2...) so we need different handling.

        Args:
            ax: Matplotlib axes object
            style: Style dictionary (DESKTOP or MOBILE)
            tick_size: Font size for tick labels
        """
        # Extract years from the stored original categories
        if not hasattr(self, "_original_categories") or self._original_categories is None:
            # Fallback to standard formatting
            plt.setp(
                ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size
            )
            return

        try:
            # Extract years from original categories
            years = []
            for i, category in enumerate(self._original_categories):
                try:
                    if hasattr(category, "year"):  # datetime object
                        years.append((i, category.year))
                    else:
                        # Convert to string and try to parse
                        category_str = str(category).strip()
                        if category_str.isdigit() and len(category_str) == 4:
                            years.append((i, int(category_str)))
                        else:
                            # Try to extract 4-digit year from string
                            import re

                            year_match = re.search(r"\b(19|20)\d{2}\b", category_str)
                            if year_match:
                                years.append((i, int(year_match.group())))
                except (ValueError, AttributeError):
                    continue

            if not years:
                # No valid years found, use standard formatting
                plt.setp(
                    ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size
                )
                return

            # Determine year range
            year_values = [y[1] for y in years]
            min_year = min(year_values)
            max_year = max(year_values)
            year_range = max_year - min_year

            # For bar charts with categorical axes, set all year positions as ticks
            # but only label some of them based on the year range
            all_positions = [y[0] for y in years]

            # Determine which years should have labels
            labels = []
            labeled_positions = []
            for pos, year in years:
                if year_range > 20:
                    # Show only decade labels
                    if year % 10 == 0:
                        labels.append(str(year))
                        labeled_positions.append(pos)
                    else:
                        labels.append("")
                elif year_range < 10:
                    # Show all years
                    labels.append(str(year))
                    labeled_positions.append(pos)
                else:
                    # Show every 5 years
                    if year % 5 == 0:
                        labels.append(str(year))
                        labeled_positions.append(pos)
                    else:
                        labels.append("")

            # Set all positions as ticks
            ax.set_xticks(all_positions)
            ax.set_xticklabels(labels)

            # Style the ticks - all will be visible as "major" ticks
            # First, set all ticks to the shorter length
            ax.tick_params(
                axis="x",
                which="major",
                length=4,
                width=1,
                rotation=style.get("tick_rotation", 0),
                labelsize=tick_size,
            )

            # Now, adjust tick line lengths:
            # - For labeled ticks (e.g. every decade when year_range > 20), use longer ticks.
            # - Additionally, if only every 10 years are labeled (year_range > 20),
            #   make ticks for every 5-year mark slightly longer.
            for i, tick in enumerate(ax.xaxis.get_major_ticks()):
                if i < len(labels) and labels[i]:
                    tick.tick1line.set_markersize(8)
                    tick.tick2line.set_markersize(8)
                    tick.tick1line.set_linewidth(4)
                    tick.tick2line.set_linewidth(4)
                elif year_range > 20 and i < len(years):
                    year_val = years[i][1]
                    if year_val % 5 == 0:
                        tick.tick1line.set_markersize(6)
                        tick.tick2line.set_markersize(6)
                        tick.tick1line.set_linewidth(2)
                        tick.tick2line.set_linewidth(2)

        except Exception as e:
            logger.warning(f"Error in _apply_fiscal_year_bar_ticks: {e}")
            # Fallback to standard formatting
            plt.setp(
                ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size
            )
