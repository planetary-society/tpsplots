import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .chart_view import ChartView
import logging
import math

logger = logging.getLogger(__name__)

class LineChartView(ChartView):
    """Specialized view for line charts with a focus on exposing matplotlib's API."""
    
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
                  - position : str - Label position ('right', 'left', 'auto')
                  - offset : float - Distance from line endpoint (fraction of plot width)
                  - bbox : bool - Add background box to labels
                  - fontsize : int - Label font size (auto-sized based on style if None)
                  - avoid_edges : bool - Prevent labels from going off-chart
                
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
        ...     metadata={'title': 'Sales Over Time'},
        ...     stem='sales_chart',
        ...     x=['Jan', 'Feb', 'Mar'],
        ...     y=[[100, 150, 130], [80, 110, 140]],
        ...     label=['Product A', 'Product B'],
        ...     color=['blue', 'red']
        ... )
        
        Using DataFrame input:
        
        >>> df = pd.DataFrame({'Month': ['Jan', 'Feb', 'Mar'],
        ...                    'Sales': [100, 150, 130]})
        >>> line_view.line_plot(
        ...     metadata={'title': 'Monthly Sales'},
        ...     stem='monthly_sales',
        ...     data=df,
        ...     x='Month',
        ...     y='Sales'
        ... )
        
        With horizontal reference line:
        
        >>> line_view.line_plot(
        ...     metadata={'title': 'Performance vs Target'},
        ...     stem='performance',
        ...     x=months,
        ...     y=values,
        ...     hlines=100,
        ...     hline_labels='Target',
        ...     hline_colors='red'
        ... )
        """
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Create a line plot with appropriate styling.
        
        This method creates a basic figure and axes, applies consistent styling,
        and then lets matplotlib handle the actual plotting, using the provided
        kwargs directly.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments passed directly to matplotlib
            
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        
        # Intercept title and subtitle parameters
        # So we do our own custom title processing
        # in header and footer
        for text in ["title","subtitle"]:
            if kwargs.get(text):
                metadata[text] = kwargs.pop(text)
        
        
        # Extract data and handle DataFrame input if provided
        data = kwargs.pop('data', kwargs.pop('df', None))
        x = kwargs.pop('x', None)
        y = kwargs.pop('y', None)
        
        # Handle DataFrame columns or direct data arrays
        if data is not None:
            if isinstance(x, str):
                x_data = data[x]
            else:
                x_data = x
                
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
        if y_data is None and isinstance(x_data, (list, tuple, np.ndarray)):
            y_data = [x_data]
            x_data = np.arange(len(x_data))
            
        # Make sure y_data is a list for consistent handling
        if y_data is not None and not isinstance(y_data, (list, tuple)):
            y_data = [y_data]
            
        # Extract styling parameters
        color = kwargs.pop('color', kwargs.pop('c', None))
        linestyle = kwargs.pop('linestyle', kwargs.pop('ls', None)) 
        linewidth = kwargs.pop('linewidth', kwargs.pop('lw', style["line_width"]))
        markersize = kwargs.pop('markersize', kwargs.pop('ms', style["marker_size"]))
        marker = kwargs.pop('marker', None)
        alpha = kwargs.pop('alpha', None)
        label = kwargs.pop('label', kwargs.pop('labels', None))
        
        # Store line information for direct labeling
        line_colors = []
        line_labels = []
        
        # Plot each data series
        if x_data is not None and y_data is not None:
            for i, y_series in enumerate(y_data):
                # Build plot kwargs for this series
                plot_kwargs = {}
                
                # Handle list parameters for each series
                if isinstance(color, (list, tuple)) and i < len(color):
                    plot_kwargs['color'] = color[i]
                    series_color = color[i]
                elif color is not None:
                    plot_kwargs['color'] = color
                    series_color = color
                else:
                    series_color = f"C{i}"  # Default matplotlib color cycle
                    
                if isinstance(linestyle, (list, tuple)) and i < len(linestyle):
                    plot_kwargs['linestyle'] = linestyle[i]
                elif linestyle is not None:
                    plot_kwargs['linestyle'] = linestyle
                    
                if isinstance(marker, (list, tuple)) and i < len(marker):
                    plot_kwargs['marker'] = marker[i]
                elif marker is not None:
                    plot_kwargs['marker'] = marker
                    
                if isinstance(alpha, (list, tuple)) and i < len(alpha):
                    plot_kwargs['alpha'] = alpha[i]
                elif alpha is not None:
                    plot_kwargs['alpha'] = alpha
                    
                if isinstance(label, (list, tuple)) and i < len(label):
                    plot_kwargs['label'] = label[i]
                    series_label = label[i]
                elif label is not None and i == 0:
                    plot_kwargs['label'] = label
                    series_label = label
                else:
                    plot_kwargs['label'] = f"Series {i+1}"
                    series_label = f"Series {i+1}"
                
                # Store for direct labeling
                line_colors.append(series_color)
                line_labels.append(series_label)
                
                # Set linewidth and markersize from style
                plot_kwargs['linewidth'] = linewidth
                plot_kwargs['markersize'] = markersize
                
                # Apply any series-specific overrides
                series_key = f"series_{i}"
                if series_key in kwargs:
                    plot_kwargs.update(kwargs.pop(series_key))

                # Plot this series
                ax.plot(x_data, y_series, **plot_kwargs)
                # Apply standard styling to the axes
        
        self._apply_axes_styling(ax, metadata, style, x_data=x_data, y_data=y_data, 
                               line_colors=line_colors, line_labels=line_labels, **kwargs)
        
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _apply_axes_styling(self, ax, metadata, style, **kwargs):
        """
        Apply consistent styling to the axes.
        
        Args:
            ax: Matplotlib axes object
            metadata: Chart metadata dictionary 
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Additional styling parameters
        """
        # Extract axis-specific parameters
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        xticks = kwargs.pop('xticks', None)
        xticklabels = kwargs.pop('xticklabels', None)
        max_xticks = kwargs.pop('max_xticks', style.get("max_ticks"))
        x_data = kwargs.pop('x_data', None)
        
        # Extract other styling parameters
        grid = kwargs.pop('grid',None)
        tick_rotation = kwargs.pop('tick_rotation', style["tick_rotation"])
        tick_size = kwargs.pop('tick_size', style["tick_size"])
        label_size = kwargs.pop('label_size', style["label_size"])
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        scale = kwargs.pop('scale', None)
        axis_scale = kwargs.pop('axis_scale', 'y')
        
        # Handle legend and direct line labels parameters
        legend = kwargs.pop('legend', True)
        direct_line_labels = kwargs.pop('direct_line_labels', False)
        y_data = kwargs.pop('y_data', None)
        line_colors = kwargs.pop('line_colors', [])
        line_labels = kwargs.pop('line_labels', [])

        # Apply axis labels if provided
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=label_size)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=label_size)
        
        # Apply grid setting
        if (grid or style.get("grid")):
            if grid:
                ax.grid(grid)
            else:
                grid_args = {"axis":style.get("grid_axis")}
                ax.grid(**grid_args)
        
        # Explicitly set tick sizes
        tick_size = kwargs.pop('tick_size', style["tick_size"])
        ax.tick_params(axis='x', labelsize=tick_size)
        ax.tick_params(axis='y', labelsize=tick_size)
        
        # Check if we should use fiscal year tick formatting
        fiscal_year_ticks = kwargs.pop('fiscal_year_ticks', True)
        
        # Apply appropriate tick formatting
        if fiscal_year_ticks and x_data is not None and self._contains_dates(x_data):
            # Apply special FY formatting
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
        elif x_data is not None and self._contains_dates(x_data):
            import matplotlib.dates as mdates
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)
        else:
            # Apply standard tick formatting
            plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
            plt.setp(ax.get_yticklabels(), fontsize=tick_size)
            
            # Check if x_data is categorical (strings)
            is_categorical = x_data is not None and len(x_data) > 0 and isinstance(x_data[0], str)
            
            # Set tick locators if needed
            if max_xticks and not is_categorical:
                # Only apply MaxNLocator for numeric data
                ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
            elif is_categorical and max_xticks and len(x_data) > max_xticks:
                # For categorical data, thin the ticks by showing every nth tick
                step = len(x_data) // max_xticks + 1
                tick_positions = list(range(0, len(x_data), step))
                ax.set_xticks(tick_positions)
                ax.set_xticklabels([x_data[i] for i in tick_positions])
        
        # Apply scale formatter if specified
        if scale:
            self._apply_scale_formatter(ax, scale, axis_scale)
        
        # Apply custom limits
        if xlim:
            if isinstance(xlim,dict):
                ax.set_xlim(**xlim)
            else:
                ax.set_xlim(xlim)
        if ylim:
            if isinstance(ylim,dict):
                ax.set_ylim(**ylim)
            else:
                ax.set_ylim(ylim)
        
        # Apply custom ticks
        if xticks is not None:
            ax.set_xticks(xticks)
            if xticklabels is not None:
                ax.set_xticklabels(xticklabels)
            elif all(isinstance(x, (int, float)) and float(x).is_integer() for x in xticks):
                ax.set_xticklabels([f"{int(x)}" for x in xticks])
            # Apply legend explicitly using the line objects and their labels
    
        # Apply horizontal lines if specified
        self._apply_horizontal_lines(ax, **kwargs)
    
        # Handle labeling - either direct line labels or traditional legend
        if direct_line_labels and y_data is not None and line_colors and line_labels:
            # Use direct line endpoint labels instead of legend
            self._add_direct_line_endpoint_labels(
                ax, x_data, y_data, line_labels, line_colors, style, 
                direct_line_labels=direct_line_labels
            )
        elif legend:
            # Use traditional legend
            legend_kwargs = {'fontsize': style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)
            ax.legend(**legend_kwargs)

    # Add this method to your LineChartView class in tpsplots/views/line_chart.py

    # Enhanced _apply_horizontal_lines method with direct labeling

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
        hlines = kwargs.pop('hlines', kwargs.pop('horizontal_lines', None))
        
        if hlines is None:
            return
        
        # Get label positioning parameters
        label_position = kwargs.pop('hline_label_position', 'right')
        label_offset = kwargs.pop('hline_label_offset', 0.02)  # As fraction of plot width
        label_fontsize = kwargs.pop('hline_label_fontsize', 12)
        label_bbox = kwargs.pop('hline_label_bbox', True)
        
        # Handle dict format for more complex styling
        if isinstance(hlines, dict):
            y_values = []
            labels = []
            
            for y_value, line_kwargs in hlines.items():
                # Extract label from line_kwargs if present
                label = line_kwargs.pop('label', None)
                
                # Set default line styling
                default_kwargs = {
                    'color': 'gray',
                    'linestyle': '--',
                    'linewidth': 2,
                    'alpha': 0.7,
                    'zorder': 0
                }
                default_kwargs.update(line_kwargs)
                
                # Draw the line (without label since we'll add it manually)
                ax.axhline(y=y_value, **default_kwargs)
                
                # Store for label positioning
                if label:
                    y_values.append(y_value)
                    labels.append((label, default_kwargs.get('color', 'gray')))
            
            # Add direct labels
            if y_values and labels:
                self._add_direct_line_labels(ax, y_values, labels, label_position, 
                                        label_offset, label_fontsize, label_bbox)
            return
        
        # Handle single value or list of values
        if not isinstance(hlines, (list, tuple)):
            hlines = [hlines]
        
        # Extract styling parameters with defaults
        hline_colors = kwargs.pop('hline_colors', ['gray'] * len(hlines))
        hline_styles = kwargs.pop('hline_styles', ['--'] * len(hlines))
        hline_widths = kwargs.pop('hline_widths', [2] * len(hlines))
        hline_labels = kwargs.pop('hline_labels', [None] * len(hlines))
        hline_alpha = kwargs.pop('hline_alpha', [0.7] * len(hlines))
        
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
                zorder=0
            )
        
        # Add direct labels for lines that have them
        labeled_y_values = []
        labeled_info = []
        
        for i, (y_value, label) in enumerate(zip(hlines, hline_labels)):
            if label:
                labeled_y_values.append(y_value)
                labeled_info.append((label, hline_colors[i]))
        
        if labeled_y_values:
            self._add_direct_line_labels(ax, labeled_y_values, labeled_info, 
                                    label_position, label_offset, label_fontsize, label_bbox)

    def _add_direct_line_labels(self, ax, y_values, label_info, position='right', 
                            offset=0.02, fontsize=12, add_bbox=True):
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
        
        if position == 'right':
            x_pos = xlim[1] - (offset * x_range)
            ha = 'right'
        elif position == 'left':
            x_pos = xlim[0] + (offset * x_range)
            ha = 'left'
        else:  # center
            x_pos = xlim[0] + 0.5 * x_range
            ha = 'center'
        
        # Sort labels by y-value to handle overlapping
        sorted_labels = sorted(zip(y_values, label_info), key=lambda x: x[0])
        
        # Adjust y-positions to prevent overlap
        adjusted_positions = self._adjust_label_positions(
            [y for y, _ in sorted_labels], y_range * 0.02  # 2% of plot height minimum spacing
        )
        
        # Add each label
        for i, ((y_val, (label_text, color)), adj_y) in enumerate(zip(sorted_labels, adjusted_positions)):
            
            # Create bbox styling if requested
            bbox_props = None
            if add_bbox:
                bbox_props = dict(
                    boxstyle="round,pad=0.3",
                    facecolor='white',
                    edgecolor=color,
                    alpha=0.9,
                    linewidth=1
                )
            
            # Add the text label
            ax.text(
                x_pos, adj_y,
                label_text,
                fontsize=fontsize,
                ha=ha,
                va='center',
                color=color,
                fontweight='bold',
                bbox=bbox_props,
                zorder=10  # Make sure labels appear on top
            )
            
            # If we adjusted the position, draw a small line connecting to the actual line
            if abs(adj_y - y_val) > y_range * 0.01:  # Only if significantly moved
                # Draw a thin connecting line
                connect_x = x_pos + (0.01 * x_range if ha == 'right' else -0.01 * x_range)
                ax.plot([connect_x, x_pos], [y_val, adj_y], 
                    color=color, linewidth=1, alpha=0.5, zorder=5)

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
            prev_adjusted = adjusted[i-1]
            
            # If too close to previous label, push it up
            if current_y - prev_adjusted < min_spacing:
                adjusted.append(prev_adjusted + min_spacing)
            else:
                adjusted.append(current_y)
        
        return adjusted
    
    def _add_direct_line_endpoint_labels(self, ax, x_data, y_data, labels, colors, style, **kwargs):
        """
        Add labels directly on chart near line endpoints instead of using a legend.
        
        Args:
            ax: Matplotlib axes object
            x_data: X-axis data
            y_data: List of y-data arrays for each line
            labels: List of label texts for each line
            colors: List of colors for each line
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Direct line label configuration options
        """
        # Extract configuration options
        config = kwargs.get('direct_line_labels', {})
        if not isinstance(config, dict):
            config = {}  # Use defaults if just True was passed
            
        position = config.get('position', 'auto')
        offset = config.get('offset', 0.02)  # Fraction of plot width
        add_bbox = config.get('bbox', True)
        fontsize = config.get('fontsize', style.get('legend_size', 12))
        avoid_edges = config.get('avoid_edges', True)
        
        # Get axis limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        # Prepare line data for collision detection
        all_line_data = []
        for y_series in y_data:
            # Convert categorical x_data to numeric indices for collision detection
            if isinstance(x_data, (list, tuple)):
                numeric_x = list(range(len(x_data)))
            else:
                numeric_x = x_data
            all_line_data.append((numeric_x, y_series))
        
        # Collect endpoint information and find optimal positions
        label_positions = []
        existing_labels = []  # Track placed labels for collision avoidance
        
        for i, (y_series, label_text, color) in enumerate(zip(y_data, labels, colors)):
            # Find the last non-None point in the series
            last_x_idx = len(y_series) - 1
            last_y = y_series[last_x_idx]
            
            # Handle None values at the end (like our FY2025 September data)
            while last_y is None and last_x_idx > 0:
                last_x_idx -= 1
                last_y = y_series[last_x_idx]
            
            if last_y is None:
                continue  # Skip if entire series is None
                
            # Get the x position for this endpoint
            if isinstance(x_data, (list, tuple)):
                last_x = last_x_idx  # Use index position for categorical data
            else:
                last_x = x_data[last_x_idx]
            
            # Use advanced positioning if position is 'auto', otherwise use simple positioning
            if position == 'auto':
                # Find optimal position using collision detection
                optimal_pos = self._find_optimal_label_position(
                    last_x, last_y, label_text, all_line_data, 
                    existing_labels, xlim, ylim, offset, style
                )
                
                label_x = optimal_pos['x']
                label_y = optimal_pos['y']
                ha = optimal_pos['ha']
                va = optimal_pos['va']
                
                # Store bounding box for future collision detection  
                base_text_size = offset * min(x_range, y_range)
                text_width = len(label_text) * 0.5 * base_text_size
                text_height = 1.0 * base_text_size
                
                if ha == 'left':
                    bbox_x1, bbox_x2 = label_x, label_x + text_width
                elif ha == 'right':
                    bbox_x1, bbox_x2 = label_x - text_width, label_x
                else:
                    bbox_x1, bbox_x2 = label_x - text_width/2, label_x + text_width/2
                    
                if va == 'bottom':
                    bbox_y1, bbox_y2 = label_y, label_y + text_height
                elif va == 'top':
                    bbox_y1, bbox_y2 = label_y - text_height, label_y
                else:
                    bbox_y1, bbox_y2 = label_y - text_height/2, label_y + text_height/2
                
                # Add to existing labels for next iteration
                existing_labels.append({
                    'bbox_x1': bbox_x1, 'bbox_y1': bbox_y1,
                    'bbox_x2': bbox_x2, 'bbox_y2': bbox_y2
                })
                
            else:
                # Use simple positioning for non-auto modes
                if position == 'right':
                    label_x = last_x + (offset * x_range)
                    label_y = last_y
                    ha = 'left'
                    va = 'center'
                elif position == 'left':
                    label_x = last_x - (offset * x_range)
                    label_y = last_y
                    ha = 'right'
                    va = 'center'
                elif position == 'above':
                    label_x = last_x
                    label_y = last_y + (offset * y_range)
                    ha = 'center'
                    va = 'bottom'
                else:  # below
                    label_x = last_x
                    label_y = last_y - (offset * y_range)
                    ha = 'center'
                    va = 'top'
            
            # Store position info
            label_positions.append({
                'x': label_x,
                'y': label_y,
                'text': label_text,
                'color': color,
                'ha': ha,
                'va': va,
                'original_y': last_y
            })
        
        # Add labels to the plot
        for pos_info in label_positions:
            # Create bbox styling if requested
            bbox_props = None
            if add_bbox:
                bbox_props = dict(
                    boxstyle="round,pad=0.3",
                    facecolor='white',
                    edgecolor=pos_info['color'],
                    alpha=0.9,
                    linewidth=1
                )
            
            # Add the text label
            ax.text(
                pos_info['x'], pos_info['y'],
                pos_info['text'],
                fontsize=fontsize,
                ha=pos_info['ha'],
                va=pos_info['va'],
                color=pos_info['color'],
                fontweight='bold',
                bbox=bbox_props,
                zorder=10  # Make sure labels appear on top
            )
    
    def _avoid_label_collisions(self, label_positions, min_spacing):
        """
        Adjust label positions to prevent overlapping, focusing on y-axis collisions.
        
        Args:
            label_positions: List of position dictionaries
            min_spacing: Minimum spacing between labels
            
        Returns:
            List of adjusted position dictionaries
        """
        if len(label_positions) <= 1:
            return label_positions
        
        # Sort by y-position to handle overlaps systematically
        sorted_positions = sorted(label_positions, key=lambda x: x['y'])
        
        # Adjust positions to prevent overlap
        for i in range(1, len(sorted_positions)):
            current = sorted_positions[i]
            previous = sorted_positions[i-1]
            
            # Check if labels are too close vertically
            if abs(current['y'] - previous['y']) < min_spacing:
                # Move current label up to maintain spacing
                current['y'] = previous['y'] + min_spacing
                current['va'] = 'bottom'  # Adjust vertical alignment
        
        return sorted_positions
    
    def _find_optimal_label_position(self, endpoint_x, endpoint_y, text, all_line_data, 
                                   existing_labels, xlim, ylim, offset, style=None):
        """
        Find optimal label position using clockwise search from right position.
        
        Args:
            endpoint_x, endpoint_y: Line endpoint coordinates
            text: Label text for size estimation
            all_line_data: List of (x_data, y_data) tuples for all lines
            existing_labels: Previously placed label positions
            xlim, ylim: Chart axis limits (tuples)
            offset: Distance from endpoint as fraction of plot size
            style: Style dictionary for marker size info
            
        Returns:
            dict: Optimal position with coordinates and alignment
        """
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        # Convert offset to actual distance with modest spacing improvement
        base_distance = offset * min(x_range, y_range)
        
        # Small increase for better visual separation without going overboard
        offset_distance = base_distance * 1.2
        
        # Estimate text dimensions (more conservative for better spacing)
        text_width = len(text) * 0.5 * base_distance  # Rough character width
        text_height = 1.0 * base_distance  # Rough text height
        
        best_position = None
        best_score = float('inf')
        
        # Try positions in 5-degree increments, starting from right (0°)
        for angle_deg in range(0, 360, 5):
            angle_rad = math.radians(angle_deg)
            
            # Calculate position coordinates
            label_x = endpoint_x + offset_distance * math.cos(angle_rad)
            label_y = endpoint_y + offset_distance * math.sin(angle_rad)
            
            # Determine text alignment based on angle
            if -45 <= angle_deg <= 45 or 315 <= angle_deg <= 360:
                ha = 'left'
            elif 135 <= angle_deg <= 225:
                ha = 'right'
            else:
                ha = 'center'
                
            if 45 <= angle_deg <= 135:
                va = 'bottom'
            elif 225 <= angle_deg <= 315:
                va = 'top'
            else:
                va = 'center'
            
            # Calculate label bounding box
            if ha == 'left':
                bbox_x1, bbox_x2 = label_x, label_x + text_width
            elif ha == 'right':
                bbox_x1, bbox_x2 = label_x - text_width, label_x
            else:  # center
                bbox_x1, bbox_x2 = label_x - text_width/2, label_x + text_width/2
                
            if va == 'bottom':
                bbox_y1, bbox_y2 = label_y, label_y + text_height
            elif va == 'top':
                bbox_y1, bbox_y2 = label_y - text_height, label_y
            else:  # center
                bbox_y1, bbox_y2 = label_y - text_height/2, label_y + text_height/2
            
            # Score this position
            score = self._score_label_position(
                bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                endpoint_x, endpoint_y, all_line_data, existing_labels,
                xlim, ylim, angle_deg
            )
            
            # Track best position
            if score < best_score:
                best_score = score
                best_position = {
                    'x': label_x,
                    'y': label_y,
                    'ha': ha,
                    'va': va,
                    'score': score,
                    'angle': angle_deg
                }
        
        # If all positions are bad, use fallback (below position)
        if best_score > 100:  # Arbitrary threshold for "very bad"
            fallback_position = {
                'x': endpoint_x,
                'y': endpoint_y - offset_distance,
                'ha': 'center',
                'va': 'top',
                'score': best_score,
                'angle': 270
            }
            return fallback_position
            
        return best_position
    
    def _score_label_position(self, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                            endpoint_x, endpoint_y, all_line_data, existing_labels,
                            xlim, ylim, angle_deg):
        """
        Score a label position based on various collision and preference factors.
        
        Args:
            bbox_x1, bbox_y1, bbox_x2, bbox_y2: Label bounding box
            endpoint_x, endpoint_y: Line endpoint coordinates
            all_line_data: List of (x_data, y_data) tuples for all lines
            existing_labels: Previously placed label positions
            xlim, ylim: Chart axis limits
            angle_deg: Angle from right position in degrees
            
        Returns:
            float: Score (lower is better)
        """
        score = 0
        
        # Penalty for distance from preferred right position (0°)
        angle_penalty = min(angle_deg, 360 - angle_deg) / 5.0  # 1 point per 5°
        score += angle_penalty
        
        # Heavy penalty for going outside chart bounds
        if (bbox_x1 < xlim[0] or bbox_x2 > xlim[1] or 
            bbox_y1 < ylim[0] or bbox_y2 > ylim[1]):
            score += 50
        
        # Penalty for overlapping with existing labels
        for existing_label in existing_labels:
            if self._boxes_overlap(bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                                 existing_label.get('bbox_x1', 0),
                                 existing_label.get('bbox_y1', 0),
                                 existing_label.get('bbox_x2', 0),
                                 existing_label.get('bbox_y2', 0)):
                score += 20
        
        # Penalty for overlapping with line segments
        for x_data, y_data in all_line_data:
            if self._label_intersects_line(bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                                         x_data, y_data):
                score += 10
        
        # Penalty for being too close to the endpoint (encourage more separation)
        label_center_x = (bbox_x1 + bbox_x2) / 2
        label_center_y = (bbox_y1 + bbox_y2) / 2
        distance_to_endpoint = math.sqrt((label_center_x - endpoint_x)**2 + 
                                       (label_center_y - endpoint_y)**2)
        
        # Increased minimum distance to ensure clear separation from endpoints
        min_distance = 0.12 * min(xlim[1] - xlim[0], ylim[1] - ylim[0])
        if distance_to_endpoint < min_distance:
            score += 50  # Strong penalty to force labels away from endpoints
        
        return score
    
    def _boxes_overlap(self, x1a, y1a, x2a, y2a, x1b, y1b, x2b, y2b):
        """Check if two rectangular boxes overlap."""
        return not (x2a < x1b or x2b < x1a or y2a < y1b or y2b < y1a)
    
    def _label_intersects_line(self, bbox_x1, bbox_y1, bbox_x2, bbox_y2, x_data, y_data):
        """
        Check if label bounding box intersects with any line segments.
        
        This is a simplified check - we test if any line points fall within the bbox
        or if the line crosses through the bbox boundaries.
        """
        # Simple point-in-box check for line vertices
        for i, (x, y) in enumerate(zip(x_data, y_data)):
            if y is None:  # Skip None values
                continue
            if bbox_x1 <= x <= bbox_x2 and bbox_y1 <= y <= bbox_y2:
                return True
        
        # Check if any line segment crosses the bounding box
        # (Simplified - just check if line crosses box center)
        box_center_x = (bbox_x1 + bbox_x2) / 2
        box_center_y = (bbox_y1 + bbox_y2) / 2
        
        for i in range(len(x_data) - 1):
            if y_data[i] is None or y_data[i+1] is None:
                continue
                
            x1, y1 = x_data[i], y_data[i]
            x2, y2 = x_data[i+1], y_data[i+1]
            
            # Simple distance check to box center
            dist_to_line = self._point_to_line_distance(
                box_center_x, box_center_y, x1, y1, x2, y2
            )
            
            # If line passes close to label center, consider it a collision
            if dist_to_line < min(bbox_x2 - bbox_x1, bbox_y2 - bbox_y1) / 3:
                return True
        
        return False
    
    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate perpendicular distance from point to line segment."""
        # Line segment length
        line_length_sq = (x2 - x1)**2 + (y2 - y1)**2
        
        if line_length_sq == 0:
            # Point-to-point distance
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Parameter t for projection of point onto line
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length_sq))
        
        # Closest point on line segment
        closest_x = x1 + t * (x2 - x1)
        closest_y = y1 + t * (y2 - y1)
        
        # Distance from point to closest point
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)