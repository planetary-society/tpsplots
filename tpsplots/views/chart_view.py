from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from matplotlib.ticker import FuncFormatter
import numpy as np
import math
from pathlib import Path
import matplotlib.pyplot as plt
from pywaffle import Waffle
import warnings

class ChartView:
    """View component for chart generation with desktop/mobile versions built in."""
    TPS_STYLE = Path(__file__).parent.parent / "style" / "tps_base.mplstyle"
    # Load global style once at class initialization
    plt.style.use(TPS_STYLE)
    
    # Shared color palette
    COLORS = {
        "blue": "#037CC2",
        "purple": "#643788",
        "orange": "#FF5D47",
        "light_blue": "#80BDE0",
        "light_purple": "#B19BC3",
        "lunar_dust": "#8C8C8C",
        "dark_gray": "#414141",
        "medium_gray": "#C3C3C3",
        "light_gray": "#F5F5F5"
    }
    
    TPS_COLORS = {
        "Light Plasma": "#D8CDE1",
        "Medium Plasma": "#B19BC3",
        "Plasma Purple": "#643788",
        "Rocket Flame": "#FF5D47",
        "Neptune Blue": "#037CC2",
        "Medium Neptune": "#80BDE0",
        "Light Neptune": "#BFDEF0",
        "Crater Shadow": "#414141",
        "Lunar Soil": "#8C8C8C",
        "Comet Dust": "#C3C3C3",
        "Slushy Brine": "#F5F5F5",
        "Black Hole": "#000000",
        "Polar White": "#FFFFFF",
    }

    # Device-specific visual settings
    DESKTOP = {
        "figsize": (16, 9),
        "dpi": 300,
        "title_size": 20,
        "label_size": 15,
        "tick_size": 16,
        "legend_size": 12,
        "line_width": 4,
        "marker_size": 5,
        "grid": True,
        "tick_rotation": 90,
        "add_logo": True,
        "max_ticks": 25,
    }
    
    MOBILE = {
        "figsize": (8, 8),
        "dpi": 300,
        "title_size": 18,
        "label_size": 15,
        "tick_size": 15,
        "legend_size": 9,
        "line_width": 3,
        "marker_size": 5,
        "grid": True,
        "tick_rotation": 0,
        "max_ticks": 5,
        "add_logo": True,
    }
    
    def __init__(self, outdir: Path = Path("charts")):
        self.outdir = outdir
        self.outdir.mkdir(parents=True, exist_ok=True)
    
    def line_plot(self, metadata, stem: str, **kwargs):
        """
        Generate line charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments passed to matplotlib plotting functions, including:
            - x: array-like - X-axis data points (required)
            - y: list of array-like - Y-axis data series (required if not using data/df)
            - data: DataFrame - Data source when using DataFrame column references
            - df: DataFrame - Alias for data
            - color/c: str or list - Colors for the plot series
            - linestyle/ls: str or list - Line styles for the plot series
            - linewidth/lw: float or list - Line widths for the plot series
            - marker: str or list - Marker styles for the plot series
            - markersize/ms: float or list - Marker sizes for the plot series
            - label: str or list - Labels for the legend
            - alpha: float or list - Transparency values for the plot series
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        # Generate desktop version
        desktop_fig = self._create_line_plot(
            metadata, 
            style=self.DESKTOP,
            **kwargs
        )
        self._save_chart(desktop_fig, f"{stem}_desktop", create_pptx=True)
        
        # Generate mobile version
        mobile_fig = self._create_line_plot(
            metadata, 
            style=self.MOBILE,
            **kwargs
        )
        self._save_chart(mobile_fig, f"{stem}_mobile", create_pptx=False)
        
        return {
            'desktop': desktop_fig,
            'mobile': mobile_fig
        }

    def _create_line_plot(self, metadata, style, **kwargs):
        """
        Internal method to create a line plot with appropriate styling.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc.)
        style : dict
            Device-specific styling to apply
        **kwargs : dict
            Matplotlib-compatible plot parameters
        """
        # Extract figure parameters
        figsize = kwargs.pop('figsize', style["figsize"])
        dpi = kwargs.pop('dpi', style["dpi"])
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # Extract data sources
        data = kwargs.pop('data', kwargs.pop('df', None))
        x = kwargs.pop('x', None)
        y = kwargs.pop('y', None)
        
        # Handle alternative data inputs
        if x is None and 'x_data' in kwargs:
            x = kwargs.pop('x_data')
        if y is None and 'y_data_list' in kwargs:
            y = kwargs.pop('y_data_list')
        
        # Validate data
        if x is None:
            raise ValueError("X-axis data must be provided via 'x' or 'x_data'")
        
        # Handle DataFrame input
        if data is not None:
            if isinstance(x, str):
                x = data[x]
            if isinstance(y, (list, tuple)) and all(isinstance(item, str) for item in y):
                y = [data[col] for col in y]
            elif isinstance(y, str):
                y = [data[y]]
        
        # Handle single y series
        if y is None and isinstance(x, (list, tuple, np.ndarray)):
            y = [x]
            x = np.arange(len(x))
        
        # Validate y data
        if y is None:
            raise ValueError("Y-axis data must be provided")
        
        # Ensure y is a list for consistent handling
        if not isinstance(y, (list, tuple)):
            y = [y]
        
        # Extract plot-specific parameters
        color = kwargs.pop('color', kwargs.pop('c', None))
        linestyle = kwargs.pop('linestyle', kwargs.pop('ls', None)) 
        label = kwargs.pop('label', kwargs.pop('labels', None))
        linewidth = kwargs.pop('linewidth', kwargs.pop('lw', style["line_width"]))
        markersize = kwargs.pop('markersize', kwargs.pop('ms', style["marker_size"]))
        marker = kwargs.pop('marker', None)
        alpha = kwargs.pop('alpha', None)
        
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
        
        # Plot each series
        for i, y_data in enumerate(y):
            # Common plot parameters
            plot_kwargs = {}
            
            # Handle list parameters for this series
            if isinstance(color, (list, tuple)) and i < len(color):
                plot_kwargs['color'] = color[i]
            elif color is not None and i == 0:
                plot_kwargs['color'] = color
                
            if isinstance(linestyle, (list, tuple)) and i < len(linestyle):
                plot_kwargs['linestyle'] = linestyle[i]
            elif linestyle is not None and i == 0:
                plot_kwargs['linestyle'] = linestyle
                
            if isinstance(marker, (list, tuple)) and i < len(marker):
                plot_kwargs['marker'] = marker[i]
            elif marker is not None and i == 0:
                plot_kwargs['marker'] = marker
                
            if isinstance(alpha, (list, tuple)) and i < len(alpha):
                plot_kwargs['alpha'] = alpha[i]
            elif alpha is not None and i == 0:
                plot_kwargs['alpha'] = alpha
                
            if isinstance(label, (list, tuple)) and i < len(label):
                plot_kwargs['label'] = label[i]
            elif label is not None and i == 0:
                plot_kwargs['label'] = label
            else:
                plot_kwargs['label'] = f"Series {i+1}"
            
            # Set linewidth and markersize
            plot_kwargs['linewidth'] = linewidth
            plot_kwargs['markersize'] = markersize
            
            # Apply any series-specific overrides
            series_key = f"series_{i}"
            if series_key in kwargs:
                plot_kwargs.update(kwargs.pop(series_key))
            
            # Plot this series
            ax.plot(x, y_data, **plot_kwargs)
        
        # Apply title if in metadata
        if title := metadata.get('title'):
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
        
        # Apply scale formatter
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
            elif all(float(x).is_integer() for x in xticks):
                ax.set_xticklabels([f"{int(x)}" for x in xticks])
        
        # Set tick locators
        if max_xticks:
            ax.xaxis.set_major_locator(plt.MaxNLocator(max_xticks))
        
        # Handle legend
        if legend:
            legend_kwargs = {'fontsize': style["legend_size"]}
            if isinstance(legend, dict):
                legend_kwargs.update(legend)
            print(legend_kwargs)
            ax.legend(**legend_kwargs)
        
        # Add footer elements
        self._add_footer(fig, metadata, style)
        
        # Apply tight layout
        fig.tight_layout(rect=[0, style.get("footer_height", 0.1), 1, 1])
        
        # If any kwargs remain, try to apply them to the axes
        for key, value in kwargs.items():
            if hasattr(ax, f"set_{key}"):
                getattr(ax, f"set_{key}")(value)
        
        return fig

    def _ensure_list(self, value, length, default=None):
        """
        Ensure a value is a list of the specified length.
        
        Parameters:
        -----------
        value : any
            The value to convert to a list
        length : int
            The desired length of the list
        default : list, optional
            Default list to use if value is None
            
        Returns:
        --------
        list
            A list of the specified length
        """
        if value is None:
            if default is None:
                return [None] * length
            return default
        
        if not isinstance(value, (list, tuple)):
            return [value] * length
        
        # Ensure the list is long enough by cycling
        result = list(value)
        while len(result) < length:
            result.extend(value[:length - len(result)])
        
        return result
        
    def bar_chart(self, x_data, y_data_list, metadata, stem: str) -> None:
        """Generate bar charts for both desktop and mobile."""
        # Similar implementation to line_plot but for bar charts
        # ...
        
    def waffle_chart(self, metadata, stem: str, **kwargs) -> None:
        """
        Generate waffle charts for both desktop and mobile.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc)
        stem : str
            Base filename for outputs
        **kwargs : dict
            Keyword arguments for the waffle chart, including:
            - values: dict - Dictionary with labels as keys and values as values (required)
            - rows: int - Number of rows in the waffle chart (required)
            - colors: list - List of colors to use for different categories
            - legend: bool/dict - Whether to show a legend and legend parameters
            - And any other valid Waffle parameters
            
        Returns:
        --------
        dict
            Dictionary containing the generated figure objects {'desktop': fig, 'mobile': fig}
        """
        values = kwargs.get('values')
        if not values:
            raise ValueError("The 'values' parameter is required for waffle_chart")
        
        # Calculate the total number of rows and columns to match the aspect ratio
        if 'rows' not in kwargs or 'columns' not in kwargs:
            total_blocks = sum(values.values())
            mobile_rows, mobile_columns = self._calculate_waffle_dimensions(total_blocks, self.MOBILE["figsize"])
            desktop_rows, desktop_columns = self._calculate_waffle_dimensions(total_blocks, self.DESKTOP["figsize"])
        else:
            # Use provided values if specified
            desktop_rows = kwargs.get('rows')
            desktop_columns = kwargs.get('columns')
            mobile_rows = kwargs.get('rows')
            mobile_columns = kwargs.get('columns')
        
        # Generate desktop version
        desktop_fig = self._create_waffle_chart(
            metadata, 
            style=self.DESKTOP,
            rows=desktop_rows,
            columns=desktop_columns,
            **kwargs
        )
        self._save_chart(desktop_fig, f"{stem}_desktop", create_pptx=True)
        
        # Generate mobile (1x1) version
        
        # If lenged["ncol"] is set, cut the number of rows in half (rounding up) for mobile
        # and reduce the font size to small
        if 'legend' in kwargs and isinstance(kwargs['legend'], dict):
            if 'ncol' in kwargs['legend']:
                mobile_legend_columns = math.ceil(kwargs['legend']['ncol'] / 2) + 1
                kwargs['legend']['ncol'] = mobile_legend_columns
            kwargs['legend']['fontsize'] = "small"
        
        # Now tweak the bbox_to_anchor to nudge down slightly more
        if 'bbox_to_anchor' in kwargs['legend']:
            bbox = kwargs['legend']['bbox_to_anchor']
            kwargs['legend']['bbox_to_anchor'] = (bbox[0], bbox[1] - 0.03)
            kwargs['legend']['borderpad'] = 0
        
        # Generate mobile version
        mobile_fig = self._create_waffle_chart(
            metadata, 
            style=self.MOBILE,
            rows=mobile_rows,
            columns=mobile_columns,
            **kwargs
        )
        self._save_chart(mobile_fig, f"{stem}_mobile", create_pptx=False)
        
        return {
            'desktop': desktop_fig,
            'mobile': mobile_fig
        }

    def _create_waffle_chart(self, metadata, style, **kwargs):
        """
        Internal method to create a waffle chart with appropriate styling.
        
        Parameters:
        -----------
        metadata : dict
            Chart metadata (title, source, etc)
        style : dict
            Device-specific styling to apply
        **kwargs : dict
            Any parameters to pass to the Waffle constructor
            
        Returns:
        --------
        matplotlib.figure.Figure
            The generated figure
        """
        # Extract parameters that need special handling
        special_params = {}
        for param in ['title_fontproperties', 'labels_fontproperties']:
            if param in kwargs:
                special_params[param] = kwargs.pop(param)
        
        # Start with style defaults relevant to Waffle
        waffle_defaults = {
            'figsize': style["figsize"]
        }
        
        # Create parameters by merging defaults with provided kwargs
        # (kwargs take precedence)
        waffle_params = {**waffle_defaults, **kwargs}
        
        # Create the waffle chart
        fig = plt.figure(
            FigureClass=Waffle,
            **waffle_params
        )
        
        # Apply title from metadata
        title = metadata.get('title', '')
        if title:
            fig.suptitle(
                title,
                fontsize=style["title_size"],
                fontweight='bold',
                y=0.98
            )
        
        # Apply subtitle if present
        subtitle = metadata.get('subtitle', '')
        if subtitle:
            fig.text(
                0.5, 0.92,  # Position just below the title
                subtitle,
                fontsize=style["title_size"] * 0.5,
                ha='center',
                style='italic'
            )
        
        # Apply custom font properties if provided
        if 'title_fontproperties' in special_params:
            for title_obj in fig.findobj(plt.text.Text):
                if title_obj.get_text() == title:
                    title_obj.set_fontproperties(special_params['title_fontproperties'])
        
        # Add footer elements (line, source, logo)
        self._add_footer(fig, metadata, style)

        return fig
    
    def _calculate_waffle_dimensions(self, total_blocks, figsize):
        """
        Calculate optimal rows and columns for a waffle chart,
        accounting for footer and legend space.
        
        Parameters:
        -----------
        total_blocks : int
            Total number of blocks in the waffle chart
        figsize : tuple
            (width, height) dimensions of the figure
            
        Returns:
        --------
        tuple
            (rows, columns) optimized for the aspect ratio
        """
        import math
        
        # Extract width and height from figsize
        width, height = figsize
        
        # Reserve some portion of the image height for footer and legend
        # This effectively reduces the available height for the waffle chart
        available_height = height * 0.75
        
        # Calculate the effective aspect ratio of the available space
        effective_aspect_ratio = width / available_height
        
        # Calculate columns optimized for the effective aspect ratio
        columns = round(math.sqrt(total_blocks * effective_aspect_ratio))
        
        # Calculate rows to accommodate all blocks
        rows = math.ceil(total_blocks / columns)
        
        # Ensure we have enough rows and columns
        rows = max(rows, 1)
        columns = max(columns, 1)
        
        return rows, columns
    
    def _apply_scale_formatter(self, ax, scale='billions', axis='y', decimals=0, prefix='$'):
        """Apply scale formatting to axis."""
        scales = {
            'billions': {'factor': 1e9, 'suffix': 'B'},
            'millions': {'factor': 1e6, 'suffix': 'M'},
            'thousands': {'factor': 1e3, 'suffix': 'K'},
            'percentage': {'factor': 0.01, 'suffix': '%', 'prefix': ''}
        }

        if scale not in scales:
            warnings.warn(f"Scale '{scale}' not recognized. No formatter applied.")
            return # Exit if scale is invalid

        scale_info = scales[scale]
        factor = scale_info['factor']
        suffix = scale_info.get('suffix', '')
        # Prioritize prefix from scale_info if it exists, otherwise use the default 'prefix' argument
        prefix = scale_info.get('prefix', prefix)


        def formatter(x, pos):
            # --- Debugging and error handling inside the formatter ---
            try:
                # Ensure x is a finite number before proceeding
                if not np.isfinite(x):
                     return "Invalid" # Return a placeholder for non-finite values

                # Handle potential division by zero if factor could be zero (unlikely with these scales)
                if factor == 0:
                     return "Div/0" # Placeholder

                scaled_value = x / factor
                # Use the f-string format specifier dynamically
                format_spec = f'.{decimals}f'
                formatted_num = f'{scaled_value:{format_spec}}'

                # Combine prefix, formatted number, and suffix
                return f'{prefix}{formatted_num}{suffix}'

            except Exception as e:
                print(f"Formatter error for value x={x}, pos={pos}: {e}")
                # Return a placeholder string if formatting fails
                return "Error"
            # --- End of debugging and error handling ---

        # Apply the formatter to the specified axis/axes
        if axis in ('y', 'both'):
            ax.yaxis.set_major_formatter(FuncFormatter(formatter))
        if axis in ('x', 'both'):
            ax.xaxis.set_major_formatter(FuncFormatter(formatter))
    
    def _add_footer(self, fig, metadata, style, bottom_margin=0.1):
        """
        Add footer elements to the figure: horizontal line, source text, and logo.
        Coordinates the placement of all footer elements.
        
        Parameters:
        -----------
        fig : matplotlib.figure.Figure
            The figure to add the footer to
        metadata : dict
            Dictionary containing chart metadata
        style : dict
            Style dictionary with visual settings
        bottom_margin : float, optional
            Bottom margin to reserve for the footer
        """
        # Check if footer should be displayed
        if metadata.get('footer', True) == False:
            return
        
        # Reserve space at the bottom for footer
        fig.subplots_adjust(bottom=bottom_margin)
        
        # Add horizontal spacer line
        spacer_y = bottom_margin / 2  # Place line halfway in the margin
        self._add_horizontal_spacer(fig, y_position=spacer_y, linewidth=1)
        
        # Add source if provided
        source_text = metadata.get('source')
        if source_text:
            self._add_source(fig, source_text)

        self._add_logo(fig)
    
    
    def _add_horizontal_spacer(self, fig, y_position=None, color=None, linewidth=0.5, extent=(0.02, 0.98)):
        """Add a horizontal line spacer to the figure."""
        # Set default values if not provided
        if y_position is None:
            y_position = 0.06
        
        if color is None:
            color = "#545454"
        
        # Add the horizontal line
        fig.add_artist(plt.Line2D(
            [extent[0], extent[1]],  # x-positions (left, right)
            [y_position, y_position],  # y-positions (same for horizontal line)
            transform=fig.transFigure,  # Use figure coordinates
            color=color,
            linestyle='-',
            linewidth=linewidth
        ))
    
    def _add_logo(self, fig):
        """Add The Planetary Society logo to the figure."""
        try:
            
            logo_path = Path(__file__).parent.parent.parent / "img" / "TPS_Logo_1Line-Black.png"
            if not logo_path.exists():
                return
                
            logo = mpimg.imread(str(logo_path))
            
            # Apply color mask if the logo has an alpha channel (RGBA)
            if logo.shape[2] == 4:  # RGBA format
                # Extract alpha channel
                alpha = logo[:, :, 3]
                
                # Create a color mask for the logo to better
                # match the chart colors
                hex_color = "#545454"
                rgb_color = np.array([
                    int(hex_color[1:3], 16) / 255.0,
                    int(hex_color[3:5], 16) / 255.0,
                    int(hex_color[5:7], 16) / 255.0
                ])
                
                # Create a new image where all non-transparent pixels are the specified color
                new_logo = np.zeros((logo.shape[0], logo.shape[1], 4))
                for i in range(3):  # RGB channels
                    new_logo[:, :, i] = rgb_color[i]
                new_logo[:, :, 3] = alpha  # Preserve original alpha
                
                logo = new_logo
            
            imagebox = OffsetImage(logo, zoom=0.08)
                        
            ab = AnnotationBbox(
                imagebox, 
                xy=(0.99, 0),  # Position at right, bottom corner
                xycoords='figure fraction',
                box_alignment=(1, 0),  # Align the right edge of the logo with the xy point
                frameon=False,
                pad=0  # No padding
            )
            fig.add_artist(ab)
            
            # Ensure the figure size accommodates the logo
            # This is important to prevent the logo from extending beyond the visible area
            fig.tight_layout(rect=[0, 0.09, 1, 1])
        except Exception as e:
            print(f"Warning: Could not add logo: {e}")
    
    def _add_source(self, fig, source_text):
        """Add source text to the bottom left of the figure."""
        if not source_text:
            return
            
        # Add text at the bottom left
        fig.text(
            0.02,  # x position (left side)
            0.01,  # y position (bottom)
            f"Source: {source_text}".upper(),
            fontsize=11,
            color="#545454",
            ha='left',
            va='bottom'
        )

    def _save_chart(self, fig, filename, create_pptx=False):
        """Save chart as SVG, PNG, and optionally PPTX."""
        svg_path = self.outdir / f"{filename}.svg"
        png_path = self.outdir / f"{filename}.png"
        
        fig.savefig(svg_path, format="svg", dpi=300)
        fig.savefig(png_path, format="png", dpi=300)
        print(f"✓ saved {svg_path.name} and {png_path.name}")
        
        if create_pptx:
            pptx_path = self.outdir / f"{filename}.pptx"
            self._create_pptx(png_path, pptx_path)
            print(f"✓ saved {pptx_path.name}")
            
        plt.close(fig)

    def _create_pptx(self, png_path, pptx_path):
        """Create a PowerPoint file with the chart."""
        from pptx import Presentation
        from pptx.util import Inches, Pt
        
        prs = Presentation()
        
        # Set slide size to 16x9
        prs.slide_width = Inches(13.33)  # 16 inches wide
        prs.slide_height = Inches(7.5)  # 9 inches tall
        
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        slide.shapes.add_picture(str(png_path), Inches(0.5), Inches(0.5), width=Inches(12.33))
        prs.save(pptx_path)