"""Enhanced bar chart with automatic percentage formatting for y-axis ticks."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path
from .chart_view import ChartView
import logging

logger = logging.getLogger(__name__)

class BarChartView(ChartView):
    """Specialized view for standard bar charts with a focus on exposing matplotlib's API."""
    
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
            - value_format: str - Format for values ('monetary', 'percentage', 'integer', 'float')
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
        categories = kwargs.pop('categories', None)
        values = kwargs.pop('values', None)
        
        if categories is None or values is None:
            raise ValueError("Both 'categories' and 'values' are required for bar_plot")
        
        # Convert to numpy arrays for easier handling
        categories = np.array(categories)
        values = np.array(values)
        
        # Check for fiscal year data IMMEDIATELY on original categories
        # This must happen before any other processing that might modify the data
        fiscal_year_ticks = kwargs.pop('fiscal_year_ticks', True)
        categories_are_fiscal_years = fiscal_year_ticks and self._contains_dates(categories)
        
        # Store original categories for fiscal year range calculation
        self._original_categories = categories if categories_are_fiscal_years else None
        
        # Validate data lengths
        if len(categories) != len(values):
            raise ValueError("categories and values must have the same length")
        
        # Handle sorting if requested
        sort_by = kwargs.pop('sort_by', None)
        sort_ascending = kwargs.pop('sort_ascending', True)
        
        if sort_by:
            sorted_indices = self._get_sort_indices(categories, values, sort_by, sort_ascending)
            categories = categories[sorted_indices]
            values = values[sorted_indices]
        
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # Intercept title and subtitle parameters
        for text in ["title", "subtitle"]:
            if kwargs.get(text):
                metadata[text] = kwargs.pop(text)
        
        # Extract styling parameters
        orientation = kwargs.pop('orientation', 'vertical')
        colors = kwargs.pop('colors', None)
        positive_color = kwargs.pop('positive_color', None)
        negative_color = kwargs.pop('negative_color', None)
        show_values = kwargs.pop('show_values', False)
        value_format = kwargs.pop('value_format', 'float')
        value_offset = kwargs.pop('value_offset', None)
        value_fontsize = kwargs.pop('value_fontsize', style.get("tick_size", 12) * 0.9)
        value_color = kwargs.pop('value_color', 'black')
        value_weight = kwargs.pop('value_weight', 'normal')
        width = kwargs.pop('width', 0.8)
        height = kwargs.pop('height', 0.8)
        alpha = kwargs.pop('alpha', 1.0)
        edgecolor = kwargs.pop('edgecolor', 'white')
        linewidth = kwargs.pop('linewidth', 0.5)
        baseline = kwargs.pop('baseline', 0)
        
        # Determine colors for each bar
        bar_colors = self._determine_bar_colors(values, colors, positive_color, negative_color)
        
        # Create the bar chart
        if orientation == 'vertical':
            positions = np.arange(len(categories))
            bars = ax.bar(
                positions, values, width,
                bottom=baseline,
                color=bar_colors,
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth
            )
            ax.set_xticks(positions)
            ax.set_xticklabels(categories)
        else:  # horizontal
            positions = np.arange(len(categories))
            bars = ax.barh(
                positions, values, height,
                left=baseline,
                color=bar_colors,
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth
            )
            ax.set_yticks(positions)
            ax.set_yticklabels(categories)
        
        # Add value labels if requested
        if show_values:
            self._add_value_labels(
                ax, bars, values, orientation, value_format, 
                value_offset, value_fontsize, value_color, value_weight, baseline
            )
        
        # Apply styling (now includes percentage formatting)
        self._apply_bar_styling(ax, style, orientation, categories_are_fiscal_years, 
                               value_format=value_format, **kwargs)
        
        # Add legend if multiple colors are used and labels are provided
        legend = kwargs.pop('legend', False)
        if legend and (positive_color or negative_color):
            self._add_value_based_legend(ax, values, positive_color, negative_color, style)
        
        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _get_sort_indices(self, categories, values, sort_by, ascending=True):
        """Get indices for sorting the data."""
        if sort_by == 'value':
            sort_values = values
        elif sort_by == 'category':
            sort_values = categories
        else:
            raise ValueError(f"sort_by must be 'value' or 'category', got {sort_by}")
        
        return np.argsort(sort_values) if ascending else np.argsort(sort_values)[::-1]
    
    def _determine_bar_colors(self, values, colors, positive_color, negative_color):
        """
        Determine the color for each bar based on values and color parameters.
        
        Args:
            values: Array of bar values
            colors: Base colors (str or list)
            positive_color: Color for positive values
            negative_color: Color for negative values
            
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
    
    def _add_value_labels(self, ax, bars, values, orientation, value_format, 
                         value_offset, fontsize, color, weight, baseline):
        """Add value labels to each bar."""
        if value_offset is None:
            # Auto-calculate offset based on orientation and value range
            if orientation == 'vertical':
                value_range = ax.get_ylim()[1] - ax.get_ylim()[0]
                value_offset = value_range * 0.02  # 2% of range
            else:
                value_range = ax.get_xlim()[1] - ax.get_xlim()[0]
                value_offset = value_range * 0.02
        
        for bar, value in zip(bars, values):
            # Format the value
            formatted_value = self._format_value(value, value_format)
            
            if orientation == 'vertical':
                # Position label above or below bar depending on value
                if value >= baseline:
                    label_y = bar.get_height() + value_offset
                    va = 'bottom'
                else:
                    label_y = bar.get_height() - value_offset
                    va = 'top'
                
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    label_y,
                    formatted_value,
                    ha='center', va=va,
                    fontsize=fontsize,
                    color=color,
                    weight=weight
                )
            else:  # horizontal
                # Position label to the right or left of bar depending on value
                if value >= baseline:
                    label_x = bar.get_width() + value_offset
                    ha = 'left'
                else:
                    label_x = bar.get_width() - value_offset
                    ha = 'right'
                
                ax.text(
                    label_x,
                    bar.get_y() + bar.get_height() / 2,
                    formatted_value,
                    ha=ha, va='center',
                    fontsize=fontsize,
                    color=color,
                    weight=weight
                )
    
    def _add_value_based_legend(self, ax, values, positive_color, negative_color, style):
        """Add legend for positive/negative value colors."""
        legend_elements = []
        legend_labels = []
        
        has_positive = np.any(values >= 0)
        has_negative = np.any(values < 0)
        
        if has_positive and positive_color:
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=positive_color, edgecolor='white'))
            legend_labels.append('Positive')
        
        if has_negative and negative_color:
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=negative_color, edgecolor='white'))
            legend_labels.append('Negative')
        
        if legend_elements:
            ax.legend(legend_elements, legend_labels, 
                     loc='upper right', 
                     fontsize=style.get("legend_size", 12))
    
    def _format_value(self, value, format_type):
        """Format values according to the specified format type."""
        if pd.isna(value):
            return ""
        
        if format_type == 'monetary':
            return self._format_monetary(value)
        elif format_type == 'percentage':
            return f"{value:.1f}%"
        elif format_type == 'integer':
            return f"{int(value):,}"
        elif format_type == 'float':
            return f"{value:.1f}"
        else:
            return str(value)
    
    def _format_monetary(self, value):
        """Format monetary values with appropriate suffixes."""
        abs_value = abs(value)
        sign = "-" if value < 0 else ""
        
        if abs_value >= 1_000_000_000:
            return f"{sign}${abs_value/1_000_000_000:.1f}B"
        elif abs_value >= 1_000_000:
            return f"{sign}${abs_value/1_000_000:.0f}M"
        elif abs_value >= 1_000:
            return f"{sign}${abs_value/1_000:.0f}K"
        else:
            return f"{sign}${abs_value:.0f}"
    
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
        
        if orientation == 'vertical':
            # For vertical bars, format y-axis (value axis)
            ax.yaxis.set_major_formatter(FuncFormatter(percentage_formatter))
        else:
            # For horizontal bars, format x-axis (value axis)
            ax.xaxis.set_major_formatter(FuncFormatter(percentage_formatter))
    
    def _apply_bar_styling(self, ax, style, orientation, categories_are_fiscal_years, **kwargs):
        """Apply consistent styling to the bar chart."""
        # Extract styling parameters
        scale = kwargs.pop('scale', None)
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        grid = kwargs.pop('grid', True)
        grid_axis = kwargs.pop('grid_axis', 'y' if orientation == 'vertical' else 'x')
        tick_size = kwargs.pop('tick_size', style.get("tick_size", 12))
        tick_rotation = kwargs.pop('tick_rotation', 
                                style.get("tick_rotation", 45 if orientation == 'vertical' else 0))
        baseline = kwargs.pop('baseline', 0)
        value_format = kwargs.pop('value_format', None)  # Extract value_format
        
        # Scale down tick size on mobile display
        if style["type"] == "mobile":
            tick_size = tick_size * 0.8
        
        # Scale smaller y-axis labels
        label_size = tick_size * 0.6
        
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=label_size)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=label_size, loc="center", style='italic')
        
        # Apply grid
        if grid:
            ax.grid(axis=grid_axis, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Add baseline reference line if different from 0
        if baseline != 0:
            if orientation == 'vertical':
                ax.axhline(y=baseline, color='gray', linestyle='-', linewidth=1, alpha=0.7)
            else:
                ax.axvline(x=baseline, color='gray', linestyle='-', linewidth=1, alpha=0.7)
        
        # Disable minor ticks for both axes
        ax.xaxis.set_minor_locator(plt.NullLocator())
        ax.yaxis.set_minor_locator(plt.NullLocator())
        ax.tick_params(which='minor', left=False, right=False, top=False, bottom=False)
        
        # Apply percentage formatting if value_format is 'percentage'
        if value_format == 'percentage':
            self._apply_percentage_tick_formatter(ax, orientation)
        
        # Apply scale formatter if specified (but not if we already applied percentage formatting)
        elif scale:
            axis_to_scale = 'y' if orientation == 'vertical' else 'x'
            self._apply_scale_formatter(ax, scale, axis=axis_to_scale)
        
        # Apply appropriate tick formatting based on fiscal year detection
        if categories_are_fiscal_years and orientation == 'vertical':
            # Apply special FY formatting using the base class method
            # but with bar chart-specific xlim calculation
            self._apply_fiscal_year_bar_ticks(ax, style, tick_size=tick_size)
        else:
            # Apply standard tick formatting
            ax.tick_params(axis='x', labelsize=tick_size, rotation=tick_rotation)
            ax.tick_params(axis='y', labelsize=(tick_size*2))
            
            # Set tick locators if needed
            max_xticks = kwargs.pop('max_xticks', style.get("max_ticks"))
            if max_xticks and orientation == 'vertical':
                ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
        
    
        # Apply custom limits
        if xlim:
            if isinstance(xlim, dict):
                ax.set_xlim(**xlim)
            else:
                ax.set_xlim(xlim)
        if ylim:
            if isinstance(ylim, dict):
                ax.set_ylim(**ylim)
            else:
                ax.set_ylim(ylim)
        
        # Apply category alignment for non-fiscal year cases or when needed
        if not categories_are_fiscal_years or orientation != 'vertical':
            if orientation == 'vertical':
                self._apply_vertical_category_alignment(ax, tick_rotation)
            else:
                self._apply_horizontal_category_alignment(ax)
    
    def _apply_vertical_category_alignment(self, ax, tick_rotation):
        """Apply proper alignment for vertical bar chart category labels."""
        # For vertical bars, x-axis labels should be centered under bars
        positions = np.arange(len(ax.get_xticklabels()))
        ax.set_xticks(positions)
        
        # Adjust alignment based on rotation angle
        if abs(tick_rotation) == 90:
            ha = 'center'
            va = 'top'
        elif tick_rotation != 0:
            ha = 'right'
            va = 'top'
        else:
            ha = 'center'
            va = 'top'
        
        # Apply the alignment to all x-axis labels
        for tick in ax.get_xticklabels():
            tick.set_horizontalalignment(ha)
            tick.set_verticalalignment(va)
    
    def _apply_horizontal_category_alignment(self, ax):
        """Apply proper alignment for horizontal bar chart category labels."""
        # For horizontal bars, y-axis labels should be centered next to bars
        positions = np.arange(len(ax.get_yticklabels()))
        ax.set_yticks(positions)
        # Keep y-labels right-aligned for horizontal bars
        for tick in ax.get_yticklabels():
            tick.set_verticalalignment('center')
            tick.set_horizontalalignment('right')
            
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
        if not hasattr(self, '_original_categories') or self._original_categories is None:
            # Fallback to standard formatting
            plt.setp(ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size)
            return

        try:
            # Extract years from original categories
            years = []
            for i, category in enumerate(self._original_categories):
                try:
                    if hasattr(category, 'year'):  # datetime object
                        years.append((i, category.year))
                    else:
                        # Convert to string and try to parse
                        category_str = str(category).strip()
                        if category_str.isdigit() and len(category_str) == 4:
                            years.append((i, int(category_str)))
                        else:
                            # Try to extract 4-digit year from string
                            import re
                            year_match = re.search(r'\b(19|20)\d{2}\b', category_str)
                            if year_match:
                                years.append((i, int(year_match.group())))
                except (ValueError, AttributeError):
                    continue

            if not years:
                # No valid years found, use standard formatting
                plt.setp(ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size)
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
                        labels.append('')
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
                        labels.append('')

            # Set all positions as ticks
            ax.set_xticks(all_positions)
            ax.set_xticklabels(labels)

            # Style the ticks - all will be visible as "major" ticks
            # First, set all ticks to the shorter length
            ax.tick_params(axis='x', which='major', length=4, width=1,
                           rotation=style.get("tick_rotation", 0), labelsize=tick_size)

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
            print(f"DEBUG: Error in _apply_fiscal_year_bar_ticks: {e}")
            # Fallback to standard formatting
            plt.setp(ax.get_xticklabels(), rotation=style.get("tick_rotation", 0), fontsize=tick_size)