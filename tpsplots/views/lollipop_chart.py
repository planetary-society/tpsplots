"""Horizontal lollipop chart visualization specialized view."""
import numpy as np
import matplotlib.pyplot as plt
from .chart_view import ChartView
import logging

logger = logging.getLogger(__name__)

class LollipopChartView(ChartView):
    """Specialized view for horizontal lollipop charts with time value ranges."""
    
    def lollipop_plot(self, metadata, stem, **kwargs):
        """
        Generate horizontal lollipop charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Required parameters:
            - categories: list/array - Category labels for y-axis
            - start_values: list/array - Start values for each range (left side)
            - end_values: list/array - End values for each range (right side)
            
            Optional parameters:
            - colors: str/list - Colors for lollipops (default: uses TPS color cycle)
            - marker_size: int - Size of the circle markers (default: from style)
            - line_width: float - Width of the stem lines (default: from style)
            - marker_style: str - Matplotlib marker style (default: 'o')
            - start_marker_style: str - Marker style for start points (overrides marker_style)
            - end_marker_style: str - Marker style for end points (overrides marker_style)
            - start_marker_size: int - Size for start markers (overrides marker_size)
            - end_marker_size: int - Size for end markers (overrides marker_size)
            - start_marker_color: str/list - Color(s) for start markers (overrides colors)
            - end_marker_color: str/list - Color(s) for end markers (overrides colors)
            - start_marker_edgecolor: str/list - Edge color(s) for start markers
            - end_marker_edgecolor: str/list - Edge color(s) for end markers
            - start_marker_edgewidth: float - Edge width for start markers
            - end_marker_edgewidth: float - Edge width for end markers
            - line_style: str - Line style for stems (default: '-')
            - alpha: float - Transparency (default: 1.0)
            - sort_by: str - Sort categories by 'start', 'end', 'range', or None (default: None)
            - sort_ascending: bool - Sort direction if sort_by is specified (default: False)
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - xlim: tuple/dict - X-axis limits
            - grid: bool - Show grid (default: True)
            - grid_axis: str - Grid axis ('x', 'y', 'both', default: 'x')
            - value_labels: bool - Show value labels at end of ranges (default: False)
            - range_labels: bool - Show range duration labels (default: False)
            - start_value_labels: bool - Show start values on left side of lines (default: False)
            - end_value_labels: bool - Show end values on right side of lines (default: False)
            - category_wrap_length: int - Max characters per category label line
            - y_tick_marker: str - Custom marker for y-axis ticks (e.g., 'X', '|', '•', default: None)
            - y_tick_color: str - Color for y-axis tick markers (default: uses axis color)
            - y_axis_position: str - Position of y-axis ('left', 'right', default: 'left')
            - hide_y_spine: bool - Hide the vertical y-axis line while keeping ticks/labels (default: False)
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a horizontal lollipop chart with appropriate styling.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for lollipop chart creation
            
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        categories = kwargs.pop('categories', None)
        start_values = kwargs.pop('start_values', None)
        end_values = kwargs.pop('end_values', None)
        
        if categories is None or start_values is None or end_values is None:
            raise ValueError("categories, start_values, and end_values are required for lollipop_plot")
        
        # Convert to numpy arrays for easier manipulation
        categories = np.array(categories)
        start_values = np.array(start_values)
        end_values = np.array(end_values)
        
        # Validate data lengths
        if not (len(categories) == len(start_values) == len(end_values)):
            raise ValueError("categories, start_values, and end_values must have the same length")
        
        # Handle sorting if requested
        sort_by = kwargs.pop('sort_by', None)
        sort_ascending = kwargs.pop('sort_ascending', False)
        
        if sort_by:
            sort_indices = self._get_sort_indices(
                categories, start_values, end_values, sort_by, sort_ascending
            )
            categories = categories[sort_indices]
            start_values = start_values[sort_indices]
            end_values = end_values[sort_indices]
        
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # Extract styling parameters
        colors = kwargs.pop('colors', None)
        marker_size = kwargs.pop('marker_size', style.get("marker_size", 8) * 2)  # Larger for lollipops
        line_width = kwargs.pop('line_width', style.get("line_width", 3))
        marker_style = kwargs.pop('marker_style', 'o')
        line_style = kwargs.pop('line_style', '-')
        alpha = kwargs.pop('alpha', 1.0)
        
        # Extract individual marker customization parameters
        start_marker_style = kwargs.pop('start_marker_style', marker_style)
        end_marker_style = kwargs.pop('end_marker_style', marker_style)
        start_marker_size = kwargs.pop('start_marker_size', marker_size)
        end_marker_size = kwargs.pop('end_marker_size', marker_size)
        start_marker_color = kwargs.pop('start_marker_color', None)
        end_marker_color = kwargs.pop('end_marker_color', None)
        start_marker_edgecolor = kwargs.pop('start_marker_edgecolor', 'white')
        end_marker_edgecolor = kwargs.pop('end_marker_edgecolor', 'white')
        start_marker_edgewidth = kwargs.pop('start_marker_edgewidth', 1)
        end_marker_edgewidth = kwargs.pop('end_marker_edgewidth', 1)
        
        # Handle colors for start and end markers
        start_colors = self._get_marker_colors(start_marker_color, colors, len(categories))
        end_colors = self._get_marker_colors(end_marker_color, colors, len(categories))
        
        # Handle edge colors 
        start_edge_colors = self._get_marker_colors(start_marker_edgecolor, ['white'], len(categories))
        end_edge_colors = self._get_marker_colors(end_marker_edgecolor, ['white'], len(categories))
        
        # Create y-positions for categories
        y_positions = np.arange(len(categories))
        
        # Plot the lollipop chart
        for i, (cat, start_val, end_val) in enumerate(zip(categories, start_values, end_values)):
            y_pos = y_positions[i]
            
            # Use the main color for the stem line (fallback to default colors)
            stem_color = start_colors[i] if start_colors else self._get_default_colors(len(categories))[i]
            
            # Draw the stem line from start to end
            ax.plot([start_val, end_val], [y_pos, y_pos], 
                   color=stem_color, linewidth=line_width, linestyle=line_style, alpha=alpha)
            
            # Draw start marker
            ax.scatter([start_val], [y_pos], 
                      color=start_colors[i] if start_colors else stem_color, 
                      s=start_marker_size**2, 
                      marker=start_marker_style, 
                      alpha=alpha, 
                      zorder=5, 
                      edgecolors=start_edge_colors[i] if start_edge_colors else 'white', 
                      linewidth=start_marker_edgewidth)
            
            # Draw end marker
            ax.scatter([end_val], [y_pos], 
                      color=end_colors[i] if end_colors else stem_color, 
                      s=end_marker_size**2, 
                      marker=end_marker_style, 
                      alpha=alpha, 
                      zorder=5, 
                      edgecolors=end_edge_colors[i] if end_edge_colors else 'white', 
                      linewidth=end_marker_edgewidth)
        
        # Apply category labels and formatting
        self._format_lollipop_chart(ax, categories, y_positions, start_values, end_values, style, **kwargs)
        
        # Apply styling
        self._apply_lollipop_styling(ax, style, **kwargs)
        
        # Handle y-axis positioning if requested
        y_axis_position = kwargs.get('y_axis_position', 'left')
        if y_axis_position == 'right':
            self._move_y_axis_to_right(ax)
        
        # Handle custom y-axis tick markers (after axis positioning)
        y_tick_marker = kwargs.get('y_tick_marker', None)
        y_tick_color = kwargs.get('y_tick_color', None)
        
        if y_tick_marker:
            self._customize_y_ticks(ax, y_tick_marker, y_tick_color, y_axis_position, style)
        
        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _get_sort_indices(self, categories, start_values, end_values, sort_by, ascending=False):
        """Get indices for sorting the data."""
        if sort_by == 'start':
            sort_values = start_values
        elif sort_by == 'end':
            sort_values = end_values
        elif sort_by in ['range', 'duration']:
            sort_values = end_values - start_values
        elif sort_by == 'categories':
            sort_values = categories
        else:
            raise ValueError(f"sort_by must be 'start', 'end', 'range'/'duration', or 'categories', got {sort_by}")
        
        return np.argsort(sort_values) if ascending else np.argsort(sort_values)[::-1]
    
    def _get_default_colors(self, num_categories):
        """Get default TPS color cycle."""
        color_cycle = [
            self.TPS_COLORS["Neptune Blue"],
            self.TPS_COLORS["Plasma Purple"], 
            self.TPS_COLORS["Rocket Flame"],
            self.TPS_COLORS["Medium Neptune"],
            self.TPS_COLORS["Medium Plasma"],
            self.TPS_COLORS["Crater Shadow"]
        ]
        return [color_cycle[i % len(color_cycle)] for i in range(num_categories)]
    
    def _get_marker_colors(self, specific_colors, fallback_colors, num_categories):
        """Get colors for markers, handling various input formats."""
        if specific_colors is not None:
            # Use specific colors if provided
            if isinstance(specific_colors, str):
                return [specific_colors] * num_categories
            elif isinstance(specific_colors, (list, tuple)):
                if len(specific_colors) < num_categories:
                    # Extend colors if needed
                    return list(specific_colors) + [specific_colors[-1]] * (num_categories - len(specific_colors))
                return list(specific_colors)
        elif fallback_colors is not None:
            # Use fallback colors
            if isinstance(fallback_colors, str):
                return [fallback_colors] * num_categories
            elif isinstance(fallback_colors, (list, tuple)):
                if len(fallback_colors) < num_categories:
                    return list(fallback_colors) + [fallback_colors[-1]] * (num_categories - len(fallback_colors))
                return list(fallback_colors)
        else:
            # Use default TPS colors
            return self._get_default_colors(num_categories)
    
    def _format_lollipop_chart(self, ax, categories, y_positions, start_values, end_values, style, **kwargs):
        """Format the lollipop chart appearance."""
        # Handle category label wrapping
        category_wrap_length = kwargs.pop('category_wrap_length', style.get("label_wrap_length", 20))
        
        if category_wrap_length:
            wrapped_categories = []
            for cat in categories:
                if len(str(cat)) > category_wrap_length:
                    # Simple word wrapping
                    words = str(cat).split()
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) <= category_wrap_length:
                            current_line += (" " + word) if current_line else word
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)
                    wrapped_categories.append("\n".join(lines))
                else:
                    wrapped_categories.append(str(cat))
            categories = wrapped_categories
        
        # Set y-axis labels and positions
        ax.set_yticks(y_positions)
        ax.set_yticklabels(categories, fontsize=style.get("tick_size", 12))
        
        # Invert y-axis so first category is at top
        ax.invert_yaxis()
        
        # Add value labels if requested
        value_labels = kwargs.pop('value_labels', False)
        range_labels = kwargs.pop('range_labels', False)
        start_value_labels = kwargs.pop('start_value_labels', False)
        end_value_labels = kwargs.pop('end_value_labels', False)
        
        if value_labels or range_labels or start_value_labels or end_value_labels:
            self._add_value_labels(ax, y_positions, categories, 
                                 start_values, end_values, 
                                 value_labels, range_labels, start_value_labels, end_value_labels, style, kwargs)
    
    def _add_value_labels(self, ax, y_positions, categories, start_values, end_values, 
                         show_values, show_ranges, show_start_labels, show_end_labels, style, kwargs):
        """Add value labels to the lollipop chart."""
        # Use tick_size from kwargs if provided, otherwise fall back to style default
        category_label_size = kwargs.get('tick_size', style.get("tick_size", 12))
        
        # Get marker size for calculating offset
        marker_size = kwargs.get('marker_size', style.get("marker_size", 8) * 2)
        
        # Calculate offset based on marker size + 30%
        # Convert marker size to data coordinates (approximate)
        xlim = ax.get_xlim()
        x_range = xlim[1] - xlim[0]
        # Rough conversion: marker size in points to data coordinates
        marker_offset = (marker_size * 1.3 / 72) * (x_range / 10)  # Approximate scaling
        
        for i, (y_pos, start_val, end_val) in enumerate(zip(y_positions, start_values, end_values)):
            
            # Legacy value_labels parameter (shows both start and end)
            if show_values:
                # Add start value label
                ax.text(start_val, y_pos, f'{start_val:.0f}', 
                       ha='right', va='center', fontsize=category_label_size * 0.8,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.7))
                
                # Add end value label  
                ax.text(end_val, y_pos, f'{end_val:.0f}',
                       ha='left', va='center', fontsize=category_label_size * 0.8,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.7))
            
            # Individual start value labels (clean style)
            if show_start_labels:
                # Position to the left of the start marker by marker size + 30%
                ax.text(start_val - marker_offset, y_pos, f'{start_val:.0f}', 
                       ha='right', va='center', 
                       fontsize=category_label_size,
                       color=style.get('tick_color', self.COLORS['dark_gray']),
                       transform=ax.transData)
            
            # Individual end value labels (clean style)
            if show_end_labels:
                # Position to the right of the end marker by marker size + 30%
                ax.text(end_val + marker_offset, y_pos, f'{end_val:.0f}',
                       ha='left', va='center', 
                       fontsize=category_label_size,
                       color=style.get('tick_color', self.COLORS['dark_gray']),
                       transform=ax.transData)
            
            # Range duration labels
            if show_ranges:
                # Add range duration label at midpoint
                mid_point = (start_val + end_val) / 2
                range_val = end_val - start_val
                ax.text(mid_point, y_pos + 0.1, f'{range_val:.0f}',
                       ha='center', va='bottom', fontsize=category_label_size * 0.8,
                       style='italic', alpha=0.8)
    
    def _apply_lollipop_styling(self, ax, style, **kwargs):
        """Apply consistent styling to the lollipop chart."""
        # Extract styling parameters
        scale = kwargs.pop('scale', None)
        xlim = kwargs.pop('xlim', None)
        grid = kwargs.pop('grid', True)
        grid_axis = kwargs.pop('grid_axis', 'x')
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        tick_size = kwargs.pop('tick_size', style.get("tick_size", 12))
        hide_y_spine = kwargs.pop('hide_y_spine', False)
        
        # Apply axis labels
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=style.get("label_size", 14))
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=style.get("label_size", 14))
        
        # Apply grid
        if grid:
            ax.grid(axis=grid_axis, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # Set tick sizes
        ax.tick_params(axis='x', labelsize=tick_size)
        ax.tick_params(axis='y', labelsize=tick_size)
        
        # Explicitly disable y-axis minor ticks (categories are discrete)
        ax.yaxis.set_minor_locator(plt.NullLocator())
        ax.tick_params(axis='y', which='minor', left=False, right=False)
        
        # Handle custom y-axis tick markers
        y_tick_marker = kwargs.pop('y_tick_marker', None)
        y_tick_color = kwargs.pop('y_tick_color', None)
        
        # Note: Custom tick markers are handled after axis positioning
        
        # Apply scale formatter if specified
        if scale:
            self._apply_scale_formatter(ax, scale, axis='x')
        
        # Apply custom x-limits
        if xlim:
            if isinstance(xlim, dict):
                ax.set_xlim(**xlim)
            else:
                ax.set_xlim(xlim)
        
        # Remove top and right spines for cleaner look
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Handle y-spine visibility
        if hide_y_spine:
            ax.spines['left'].set_visible(False)
        else:
            # Make left spine less prominent
            ax.spines['left'].set_alpha(0.3)
        
        # Ensure y-axis shows all categories
        ax.set_ylim(-0.5, len(ax.get_yticklabels()) - 0.5)
    
    def _move_y_axis_to_right(self, ax):
        """Move y-axis labels and ticks to the right side of the chart."""
        # Move y-axis ticks and labels to the right
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position('right')
        
        # Update spine visibility - hide left, show right
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(True)
        ax.spines['right'].set_alpha(0)  # Make it invisible
    
    def _customize_y_ticks(self, ax, marker, color, y_axis_position, style):
        """Replace y-axis tick marks with custom markers."""
        # Hide the default tick marks
        ax.tick_params(axis='y', length=0, left=False, right=False)
        
        # Determine color
        if color is None:
            color = self.COLORS['dark_gray']
        
        # Get the current axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Set marker position based on y_axis_position parameter
        if y_axis_position == 'right':
            # When y-axis is on right, put tick markers to the left of the labels
            x_pos = xlim[1] - (xlim[1] - xlim[0]) * 0.015  # Left of the labels
            ha = 'right'
        else:
            # When y-axis is on left, put tick markers to the left of the labels  
            x_pos = xlim[0] - (xlim[1] - xlim[0]) * 0.015  # Left side with small offset
            ha = 'right'
        
        # Get the number of categories (which corresponds to y-tick positions)
        num_categories = len(ax.get_yticklabels())
        
        # Add custom markers at each category position
        for i in range(num_categories):
            y_pos = i  # Category positions are 0, 1, 2, etc.
            
            # Only add markers for positions within the plot range
            if ylim[0] <= y_pos <= ylim[1]:
                text_obj = ax.text(
                    x_pos, y_pos,
                    marker,
                    ha=ha,
                    va='center',
                    color=color,
                    fontsize=style.get('tick_size', 12),
                    fontweight='bold',
                    zorder=10,
                    clip_on=False,  # Allow text outside plot area
                    transform=ax.transData
                )