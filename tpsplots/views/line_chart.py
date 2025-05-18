import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .chart_view import ChartView


class LineChartView(ChartView):
    """Specialized view for line charts with a focus on exposing matplotlib's API."""
    
    def line_plot(self, metadata, stem, **kwargs):
        """
        Generate line charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments passed directly to matplotlib's plotting functions.
            This includes all standard matplotlib parameters for line plots.
            Special parameters:
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - legend: bool/dict - Legend display and parameters
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
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
        
        # Apply standard styling to the axes
        self._apply_axes_styling(ax, metadata, style, **kwargs)
        
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
        
        # Add footer elements
        self._add_footer(fig, metadata, style)
        
        # Apply tight layout
        fig.tight_layout(rect=[0, style.get("footer_height", 0.1), 1, 1])
        
        return fig
    
    def _apply_axes_styling(self, ax, metadata, style, **kwargs):
        """
        Apply consistent styling to the axes.
        
        Args:
            ax: Matplotlib axes
            metadata: Chart metadata
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Additional styling parameters
        """
        # Extract axis-specific parameters
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        xticks = kwargs.pop('xticks', None)
        xticklabels = kwargs.pop('xticklabels', None)
        max_xticks = kwargs.pop('max_xticks', style.get("max_ticks"))
        
        # Extract other styling parameters
        grid = kwargs.pop('grid', style["grid"])
        tick_rotation = kwargs.pop('tick_rotation', style["tick_rotation"])
        tick_size = kwargs.pop('tick_size', style["tick_size"])
        xlabel = kwargs.pop('xlabel', None)
        ylabel = kwargs.pop('ylabel', None)
        scale = kwargs.pop('scale', None)
        axis_scale = kwargs.pop('axis_scale', 'y')
        
        # Handle legend parameter
        legend = kwargs.pop('legend', True)
        
        # Apply title from metadata
        title = metadata.get('title')
        if title:
            ax.set_title(title, fontweight='bold', fontsize=style["title_size"])
        
        # Apply axis labels if provided
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=style["label_size"])
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=style["label_size"])
        
        # Apply grid setting
        ax.grid(grid)
        
        # Apply tick formatting
        plt.setp(ax.get_xticklabels(), rotation=tick_rotation, fontsize=tick_size)
        plt.setp(ax.get_yticklabels(), fontsize=tick_size)
        
        # Apply scale formatter if specified
        if scale:
            self._apply_scale_formatter(ax, scale, axis_scale)
        
        # Apply custom limits
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)
        
        # Apply custom ticks
        if xticks is not None:
            ax.set_xticks(xticks)
            if xticklabels is not None:
                ax.set_xticklabels(xticklabels)
            elif all(isinstance(x, (int, float)) and float(x).is_integer() for x in xticks):
                ax.set_xticklabels([f"{int(x)}" for x in xticks])
        
        # Set tick locators
        if max_xticks:
            ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
        
        # Handle legend
        if legend:
            legend_kwargs = {'fontsize': style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)
            ax.legend(**legend_kwargs)