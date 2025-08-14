import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .chart_view import ChartView
import logging

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
        
        # Plot each data series
        if x_data is not None and y_data is not None:
            for i, y_series in enumerate(y_data):
                # Build plot kwargs for this series
                plot_kwargs = {}
                
                # Handle list parameters for each series
                if isinstance(color, (list, tuple)) and i < len(color):
                    plot_kwargs['color'] = color[i]
                elif color is not None:
                    plot_kwargs['color'] = color
                    
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
                elif label is not None and i == 0:
                    plot_kwargs['label'] = label
                else:
                    plot_kwargs['label'] = f"Series {i+1}"
                
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
        
        self._apply_axes_styling(ax, metadata, style, x_data=x_data, **kwargs)
        
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
        
        # Handle legend parameter
        legend = kwargs.pop('legend', True)

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
    
        #Handle legend
        if legend:
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