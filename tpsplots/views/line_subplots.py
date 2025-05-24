"""Line subplots visualization specialized view."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from .chart_view import ChartView
import matplotlib.dates as mdates
import logging

logger = logging.getLogger(__name__)

class LineSubplotsView(ChartView):
    """Specialized view for creating line plots in a grid of subplots."""
    
    def line_subplots(self, metadata, stem, **kwargs):
        """
        Generate line subplot charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Required parameters:
            - subplot_data: list of dicts, each containing:
                - x: x-axis data
                - y: y-axis data (can be list for multiple lines)
                - title: subplot title
                - labels: list of labels for each line (optional)
                - colors: list of colors for each line (optional)
            - grid_shape: tuple (rows, cols) for subplot grid
            
            Optional parameters:
            - scale: str - Apply scale formatting ('billions', 'millions', etc.)
            - shared_x: bool - Share x-axis across subplots (default: True)
            - shared_y: bool - Share y-axis across subplots (default: True)
            - legend: bool/dict - Legend display and parameters
            - xlim: tuple - X-axis limits applied to all subplots
            - ylim: tuple - Y-axis limits applied to all subplots
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        return self.generate_chart(metadata, stem, **kwargs)
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Create line subplots with appropriate styling.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Arguments for subplot creation
            
        Returns:
            matplotlib.figure.Figure: The created figure
        """
        # Extract required parameters
        subplot_data = kwargs.pop('subplot_data', None)
        grid_shape = kwargs.pop('grid_shape', None)
        
        if subplot_data is None:
            raise ValueError("subplot_data is required for line_subplots")
        if grid_shape is None:
            # Auto-calculate grid shape based on number of subplots
            n_plots = len(subplot_data)
            cols = int(np.ceil(np.sqrt(n_plots)))
            rows = int(np.ceil(n_plots / cols))
            grid_shape = (rows, cols)
        
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        
        # Extract subplot parameters
        shared_x = kwargs.pop('shared_x', True)
        shared_y = kwargs.pop('shared_y', True)
        scale = kwargs.pop('scale', None)
        xlim = kwargs.pop('xlim', None)
        ylim = kwargs.pop('ylim', None)
        legend = kwargs.pop('legend', True)
        
        # Create figure and subplots
        fig, axes = plt.subplots(
            grid_shape[0], grid_shape[1],
            figsize=figsize,
            dpi=dpi,
            sharex=shared_x,
            sharey=shared_y,
            squeeze=False
        )
        
        # Flatten axes array for easier iteration
        axes_flat = axes.flatten()
        
        # Plot data in each subplot
        for idx, (ax, plot_data) in enumerate(zip(axes_flat[:len(subplot_data)], subplot_data)):
            # Extract data for this subplot
            x = plot_data.get('x')
            y = plot_data.get('y')
            subplot_title = plot_data.get('title', f'Subplot {idx+1}')
            labels = plot_data.get('labels', None)
            colors = plot_data.get('colors', None)
            linestyles = plot_data.get('linestyles', None)
            
            # Handle single y series
            if y is not None and not isinstance(y, (list, tuple)):
                y = [y]
            
            # Plot each line in this subplot
            if x is not None and y is not None:
                for i, y_series in enumerate(y):
                    # Skip if y_series is None or empty
                    if y_series is None:
                        continue
                    
                    # Convert to numpy array for easier handling
                    x_array = np.array(x)
                    y_array = np.array(y_series)
                    
                    # Remove NaN/NaT values
                    # Create a mask for valid values (not NaN and not NaT)
                    valid_mask = ~pd.isna(y_array)
                    
                    # Also check for NaT in x if it's datetime
                    if hasattr(x_array, 'dtype') and np.issubdtype(x_array.dtype, np.datetime64):
                        valid_mask &= ~pd.isna(x_array)
                    
                    # Filter out invalid values
                    x_valid = x_array[valid_mask]
                    y_valid = y_array[valid_mask]
                    
                    # Skip if no valid data points
                    if len(x_valid) == 0 or len(y_valid) == 0:
                        continue
                    
                    plot_kwargs = {}
                    
                    # Handle colors
                    if isinstance(colors, (list, tuple)) and i < len(colors):
                        plot_kwargs['color'] = colors[i]
                    elif colors is not None and not isinstance(colors, (list, tuple)):
                        plot_kwargs['color'] = colors
                    
                    # Handle linestyles
                    if isinstance(linestyles, (list, tuple)) and i < len(linestyles):
                        plot_kwargs['linestyle'] = linestyles[i]
                    elif linestyles is not None and not isinstance(linestyles, (list, tuple)):
                        plot_kwargs['linestyle'] = linestyles
                    else:
                        plot_kwargs['linestyle'] = '-'
                    
                    # Handle labels
                    if isinstance(labels, (list, tuple)) and i < len(labels):
                        plot_kwargs['label'] = labels[i]
                    elif labels is not None and i == 0:
                        plot_kwargs['label'] = labels
                    
                    # Set line properties
                    plot_kwargs['linewidth'] = style["line_width"]
                    
                    # Plot the line with valid data only
                    ax.plot(x_valid, y_valid, **plot_kwargs)
            
            # Set subplot title
            ax.set_title(subplot_title, fontsize=style["label_size"], pad=10)
            
            # Apply styling to this subplot
            self._apply_subplot_styling(ax, style, scale=scale, xlim=xlim, ylim=ylim)
            
            # Add legend if requested and labels were provided
            if legend and labels is not None:
                legend_kwargs = {'fontsize': style["legend_size"] * 0.8}
                if isinstance(legend, dict):
                    legend_kwargs.update(legend)
                ax.legend(**legend_kwargs)
        
        # Hide any unused subplots
        for idx in range(len(subplot_data), len(axes_flat)):
            axes_flat[idx].set_visible(False)
        
        # Apply tight layout before header/footer adjustment
        plt.tight_layout()
        
        # Adjust layout for header and footer
        self._adjust_layout_for_header_footer(fig, metadata, style)
        
        return fig
    
    def _apply_subplot_styling(self, ax, style, scale=None, xlim=None, ylim=None):
        """
        Apply consistent styling to each subplot.
        
        Args:
            ax: Matplotlib axes object
            style: Style dictionary (DESKTOP or MOBILE)
            scale: Scale formatter to apply
            xlim: X-axis limits
            ylim: Y-axis limits
        """
        # Apply grid
        if style.get("grid"):
            ax.grid(axis=style.get("grid_axis", "both"), alpha=0.3)
        
        # Set tick sizes
        tick_size = style["tick_size"] * 0.8  # Slightly smaller for subplots
        ax.tick_params(axis='both', labelsize=tick_size)
        
        # Apply fiscal year formatting if x-axis contains dates
        xlim_data = ax.get_xlim()
        if self._contains_dates_from_limits(xlim_data):
            self._apply_fiscal_year_ticks(ax, style, tick_size=tick_size)
        
        # Apply scale formatter if specified
        if scale:
            self._apply_scale_formatter(ax, scale, axis='y')
        
        # Apply axis limits
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)
        
        # Rotate x-axis labels for mobile
        if style == self.MOBILE:
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    def _contains_dates_from_limits(self, xlim):
        """Check if x-axis limits suggest date data."""
        try:
            # Check if limits are in matplotlib date format (large numbers)
            return xlim[0] > 10000 and xlim[1] > 10000
        except:
            return False