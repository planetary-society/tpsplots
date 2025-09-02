"""Stacked bar chart visualization specialized view."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from .chart_view import ChartView
import logging

logger = logging.getLogger(__name__)

class StackedBarChartView(ChartView):
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
            - value_format: str - Format for values ('monetary', 'percentage', 'integer', 'float')
            - value_threshold: float - Minimum percentage of total to show value label (default: 5.0)
            - value_fontsize: int - Font size for value labels (default: from style)
            - value_color: str - Color for value text (default: 'white')
            - value_weight: str - Font weight for values ('normal', 'bold', default: 'bold')
            - stack_labels: bool - Whether to show total values at end of each bar (default: False)
            - stack_label_format: str - Format for stack total labels (same options as value_format)
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
        categories = kwargs.pop('categories', None)
        values = kwargs.pop('values', None)
        
        if categories is None or values is None:
            raise ValueError("Both 'categories' and 'values' are required for stacked_bar_plot")
        
        # Convert values to DataFrame if it's a dict
        if isinstance(values, dict):
            df = pd.DataFrame(values, index=categories)
        elif isinstance(values, pd.DataFrame):
            df = values.copy()
            if df.index.tolist() != list(categories):
                df.index = categories
        else:
            raise ValueError("'values' must be a dict or DataFrame")
        
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
        labels = kwargs.pop('labels', df.columns.tolist())
        colors = kwargs.pop('colors', None)
        show_values = kwargs.pop('show_values', False)
        value_format = kwargs.pop('value_format', 'integer')
        value_threshold = kwargs.pop('value_threshold', 5.0)
        value_fontsize = kwargs.pop('value_fontsize', style.get("tick_size", 12) * 0.8)
        value_color = kwargs.pop('value_color', 'white')
        value_weight = kwargs.pop('value_weight', 'bold')
        stack_labels = kwargs.pop('stack_labels', False)
        stack_label_format = kwargs.pop('stack_label_format', value_format)
        width = kwargs.pop('width', 0.8)
        height = kwargs.pop('height', 0.8)
        alpha = kwargs.pop('alpha', 1.0)
        edgecolor = kwargs.pop('edgecolor', 'white')
        linewidth = kwargs.pop('linewidth', 0.5)
        
        # Set default colors if not provided
        if colors is None:
            colors = self._get_default_colors(len(df.columns))
        
        # Ensure colors list is long enough
        while len(colors) < len(df.columns):
            colors.extend(self._get_default_colors(len(df.columns)))
        colors = colors[:len(df.columns)]
        
        # Create the stacked bar chart
        bottom_values = kwargs.pop('bottom_values', None)
        
        if orientation == 'vertical':
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
                ax, df, orientation, value_format, value_threshold, 
                value_fontsize, value_color, value_weight, width, height
            )
        
        # Add stack total labels if requested
        if stack_labels:
            self._add_stack_labels(
                ax, df, orientation, stack_label_format, value_fontsize, 
                value_color, width, height
            )
        
        # Apply styling
        self._apply_stacked_bar_styling(ax, style, orientation, **kwargs)
        
        # Add legend
        legend = kwargs.pop('legend', True)
        if legend and labels:
            # Create legend patches
            legend_patches = [plt.Rectangle((0,0),1,1, facecolor=color, edgecolor=edgecolor)
                            for color in colors[:len(labels)]]
            
            legend_kwargs = {'fontsize': style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)
            
            ax.legend(legend_patches, labels, **legend_kwargs)
        
        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _create_vertical_stacked_bars(self, ax, df, colors, width, alpha, edgecolor, linewidth, bottom_values):
        """Create vertical stacked bars."""
        x_positions = np.arange(len(df.index))
        
        if bottom_values is None:
            bottom_values = np.zeros(len(df.index))
        else:
            bottom_values = np.array(bottom_values)
        
        for i, column in enumerate(df.columns):
            values = df[column].values
            ax.bar(
                x_positions, values, width, 
                bottom=bottom_values,
                color=colors[i],
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
                label=column
            )
            bottom_values += values
    
    def _create_horizontal_stacked_bars(self, ax, df, colors, height, alpha, edgecolor, linewidth, bottom_values):
        """Create horizontal stacked bars."""
        y_positions = np.arange(len(df.index))
        
        if bottom_values is None:
            bottom_values = np.zeros(len(df.index))
        else:
            bottom_values = np.array(bottom_values)
        
        for i, column in enumerate(df.columns):
            values = df[column].values
            ax.barh(
                y_positions, values, height,
                left=bottom_values,
                color=colors[i],
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
                label=column
            )
            bottom_values += values
    
    def _add_value_labels(self, ax, df, orientation, value_format, threshold, 
                         fontsize, color, weight, width, height):
        """Add value labels within each stack segment."""
        positions = np.arange(len(df.index))
        
        # Calculate percentages for threshold filtering
        totals = df.sum(axis=1)
        
        if orientation == 'vertical':
            bottom_values = np.zeros(len(df.index))
            for i, column in enumerate(df.columns):
                values = df[column].values
                
                for j, (value, total) in enumerate(zip(values, totals)):
                    # Check if segment is large enough to show label
                    percentage = (value / total * 100) if total > 0 else 0
                    if percentage >= threshold and value > 0:
                        # Calculate position for label (middle of segment)
                        y_pos = bottom_values[j] + value / 2
                        
                        # Format the value
                        formatted_value = self._format_value(value, value_format)
                        
                        ax.text(
                            positions[j], y_pos,
                            formatted_value,
                            ha='center', va='center',
                            fontsize=fontsize,
                            color=color,
                            weight=weight
                        )
                
                bottom_values += values
        
        else:  # horizontal
            left_values = np.zeros(len(df.index))
            for i, column in enumerate(df.columns):
                values = df[column].values
                
                for j, (value, total) in enumerate(zip(values, totals)):
                    # Check if segment is large enough to show label
                    percentage = (value / total * 100) if total > 0 else 0
                    if percentage >= threshold and value > 0:
                        # Calculate position for label (middle of segment)
                        x_pos = left_values[j] + value / 2
                        
                        # Format the value
                        formatted_value = self._format_value(value, value_format)
                        
                        ax.text(
                            x_pos, positions[j],
                            formatted_value,
                            ha='center', va='center',
                            fontsize=fontsize,
                            color=color,
                            weight=weight
                        )
                
                left_values += values
    
    def _add_stack_labels(self, ax, df, orientation, label_format, fontsize, color, width, height):
        """Add total value labels at the end of each stacked bar."""
        positions = np.arange(len(df.index))
        totals = df.sum(axis=1)
        
        if orientation == 'vertical':
            for i, total in enumerate(totals):
                formatted_total = self._format_value(total, label_format)
                ax.text(
                    positions[i], total,
                    formatted_total,
                    ha='center', va='bottom',
                    fontsize=fontsize,
                    color=self.COLORS['dark_gray'],
                    weight='bold'
                )
        else:  # horizontal
            for i, total in enumerate(totals):
                formatted_total = self._format_value(total, label_format)
                ax.text(
                    total, positions[i],
                    formatted_total,
                    ha='left', va='center',
                    fontsize=fontsize,
                    color=self.COLORS['dark_gray'],
                    weight='bold'
                )
    
    def _format_value(self, value, format_type):
        """Format values according to the specified format type."""
        if pd.isna(value) or value == 0:
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
        
        if abs_value >= 1_000_000_000:
            return f"${abs_value/1_000_000_000:.1f}B"
        elif abs_value >= 1_000_000:
            return f"${abs_value/1_000_000:.0f}M"
        elif abs_value >= 1_000:
            return f"${abs_value/1_000:.0f}K"
        else:
            return f"${abs_value:.0f}"
    
    def _apply_stacked_bar_styling(self, ax, style, orientation, **kwargs):
        """Apply consistent styling to the stacked bar chart."""
        # Extract styling parameters
        scale = kwargs.pop('scale', None)
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        grid = kwargs.pop('grid', True)
        grid_axis = kwargs.pop('grid_axis', 'y' if orientation == 'vertical' else 'x')
        tick_size = kwargs.pop('tick_size', style.get("tick_size", 12))
        
        # Auto-rotation logic for category labels
        if orientation == 'vertical':
            # Get current axis limits to calculate available width
            xlim_current = ax.get_xlim()
            chart_width = xlim_current[1] - xlim_current[0]
            num_categories = len(ax.get_xticklabels())
            
            if num_categories > 0:
                available_width_per_bar = chart_width / num_categories
                categories = [label.get_text() for label in ax.get_xticklabels()]
                
                # Determine if labels should be rotated
                should_rotate = self._should_rotate_labels(ax, categories, tick_size, available_width_per_bar)
                tick_rotation = 90 if should_rotate else 0
            else:
                tick_rotation = 0
        else:
            # For horizontal charts, don't rotate y-axis labels
            tick_rotation = 0
        
        # Allow manual override of tick rotation
        tick_rotation = kwargs.pop('tick_rotation', tick_rotation)
        
        # Apply axis labels
        label_size = style.get("label_size", 12)
        if style["type"] == "mobile":
            label_size = label_size * .8
            tick_size = tick_size * .8
        
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=label_size)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=label_size)
        
        # Apply grid
        if grid:
            ax.grid(axis=grid_axis, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Disable minor ticks for both axes
        ax.xaxis.set_minor_locator(plt.NullLocator())
        ax.yaxis.set_minor_locator(plt.NullLocator())
        ax.tick_params(which='minor', left=False, right=False, top=False, bottom=False)
        
        # Set tick sizes and rotation
        ax.tick_params(axis='x', labelsize=tick_size, rotation=tick_rotation)
        ax.tick_params(axis='y', labelsize=tick_size)
        
        # Ensure category labels are centered under bars with proper alignment for rotation
        if orientation == 'vertical':
            # For vertical bars, x-axis labels should be centered under bars
            x_positions = np.arange(len(ax.get_xticklabels()))
            ax.set_xticks(x_positions)
            
            # Adjust alignment based on rotation angle
            if abs(tick_rotation) == 90:
                # For 90-degree rotation, use left alignment (labels hang down from tick)
                ha = 'center'
                va = 'top'
            elif tick_rotation != 0:
                # For other rotations (like 45 degrees), use right alignment
                ha = 'right'
                va = 'top'
            else:
                # For no rotation, center the labels
                ha = 'center'
                va = 'top'
            
            # Apply the alignment to all x-axis labels
            for tick in ax.get_xticklabels():
                tick.set_horizontalalignment(ha)
                tick.set_verticalalignment(va)
                
        else:  # horizontal
            # For horizontal bars, y-axis labels should be centered next to bars
            y_positions = np.arange(len(ax.get_yticklabels()))
            ax.set_yticks(y_positions)
            # Horizontal bars typically don't rotate y-labels, so keep them centered
            for tick in ax.get_yticklabels():
                tick.set_verticalalignment('center')
                tick.set_horizontalalignment('right')
        
        # Apply scale formatter if specified
        if scale:
            axis_to_scale = 'y' if orientation == 'vertical' else 'x'
            self._apply_scale_formatter(ax, scale, axis=axis_to_scale)
        
        # Ensure integer-only ticks for count-based data
        # This prevents decimal values like 1.5 or 2.0 from appearing on the axis
        if orientation == 'vertical':
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        else:  # horizontal
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        
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
    
    def _measure_text_width(self, ax, text, fontsize):
        """Measure the rendered width of text in data coordinates."""
        # Create a temporary text object to measure its extent
        temp_text = ax.text(0, 0, text, fontsize=fontsize, transform=ax.transData)
        
        # Get the bounding box in display coordinates
        bbox = temp_text.get_window_extent(renderer=ax.figure.canvas.get_renderer())
        
        # Convert to data coordinates
        bbox_data = bbox.transformed(ax.transData.inverted())
        width = bbox_data.width
        
        # Remove the temporary text
        temp_text.remove()
        
        return width
    
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
    
    def _get_default_colors(self, num_colors):
        """Get default TPS color cycle."""
        color_cycle = [
            self.TPS_COLORS["Neptune Blue"],
            self.TPS_COLORS["Plasma Purple"], 
            self.TPS_COLORS["Rocket Flame"],
            self.TPS_COLORS["Medium Neptune"],
            self.TPS_COLORS["Medium Plasma"],
            self.TPS_COLORS["Crater Shadow"]
        ]
        return [color_cycle[i % len(color_cycle)] for i in range(num_colors)]