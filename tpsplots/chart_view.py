from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

class ChartView:
    """View component for chart generation with desktop/mobile versions built in."""
    
    # Load global style once at class initialization
    plt.style.use(Path(__file__).parent / "style" / "tps_base.mplstyle")
    
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
    
    # Device-specific visual settings
    DESKTOP = {
        "figsize": (16, 9),
        "dpi": 300,
        "title_size": 20,
        "label_size": 15,
        "tick_size": 16,
        "legend_size": 14,
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
        "legend_size": 12,
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
    
    def line_plot(self, x_data, y_data_list, metadata, stem: str) -> None:
        """Generate line charts for both desktop and mobile."""
        # Generate desktop version
        desktop_fig = self._create_line_plot(
            x_data, y_data_list, metadata, 
            style=self.DESKTOP
        )
        self._save_chart(desktop_fig, f"{stem}_desktop", create_pptx=True)
        
        # Generate mobile version
        mobile_fig = self._create_line_plot(
            x_data, y_data_list, metadata, 
            style=self.MOBILE
        )
        self._save_chart(mobile_fig, f"{stem}_mobile", create_pptx=False)
    
    def _create_line_plot(self, x_data, y_data_list, metadata, style):
        """Internal method to create a line plot with appropriate styling."""
        # Extract any custom matplotlib parameters from metadata
        mpl_kwargs = metadata.get('mpl_args', {})
        
        # Create figure with default or custom figure parameters
        fig_kwargs = mpl_kwargs.get('figure', {})
        figsize = fig_kwargs.get('figsize', style["figsize"])
        fig, ax = plt.subplots(figsize=figsize)
        
        # Extract metadata
        title = metadata.get('title', '')
        ylabel = metadata.get('ylabel', '')
        labels = metadata.get('labels', [f"Series {i+1}" for i in range(len(y_data_list))])
        colors = metadata.get('colors', [self.COLORS["blue"], self.COLORS["light_blue"], 
                                        self.COLORS["purple"], self.COLORS["orange"]])
        formats = metadata.get('formats', ['-', '--', '-.', ':'])
        scale = metadata.get('scale', None)
        
        # Create the line plot - allow series-specific styling
        for i, y_data in enumerate(y_data_list):
            # Get default style for this series
            color = colors[i % len(colors)]
            format = formats[i % len(formats)]
            linewidth = style["line_width"]
            label = labels[i]
            
            # Override with series-specific styling if provided
            series_kwargs = mpl_kwargs.get(f'series_{i}', {})
            plot_kwargs = {
                'color': series_kwargs.get('color', color),
                'linestyle': series_kwargs.get('linestyle', format),
                'linewidth': series_kwargs.get('linewidth', linewidth),
                'label': series_kwargs.get('label', label)
            }
            
            # Add any additional series-specific parameters 
            for key, value in series_kwargs.items():
                if key not in plot_kwargs:
                    plot_kwargs[key] = value
            
            # Plot the series with all parameters
            ax.plot(x_data, y_data, **plot_kwargs)
        
        # Apply styling with potential overrides
        title_kwargs = mpl_kwargs.get('title', {})
        if title is not None:
            ax.set_title(title, 
                        fontweight=title_kwargs.get('fontweight', 'bold'), 
                        fontsize=title_kwargs.get('fontsize', style["title_size"]))
        
        # Apply axis labels with potential overrides
        ylabel_kwargs = mpl_kwargs.get('ylabel', {})
        ax.set_ylabel(ylabel, fontsize=ylabel_kwargs.get('fontsize', style["label_size"]))
        
        # Apply tick formatting with potential overrides
        xtick_kwargs = mpl_kwargs.get('xtick', {})
        plt.setp(ax.get_xticklabels(), 
                rotation=xtick_kwargs.get('rotation', style["tick_rotation"]), 
                fontsize=xtick_kwargs.get('fontsize', style["tick_size"]))
        
        if style["tick_rotation"] > 0 and xtick_kwargs.get('ha') is None:
            plt.setp(ax.get_xticklabels(), ha=xtick_kwargs.get('ha', 'center'))
            
        ytick_kwargs = mpl_kwargs.get('ytick', {})
        plt.setp(ax.get_yticklabels(), 
                fontsize=ytick_kwargs.get('fontsize', style["tick_size"]))
        
        # Apply other axes customizations
        axes_kwargs = mpl_kwargs.get('axes', {})
        
        # Apply xlim/ylim if provided
        if 'xlim' in axes_kwargs:
            ax.set_xlim(axes_kwargs['xlim'])
        if 'ylim' in axes_kwargs:
            ax.set_ylim(axes_kwargs['ylim'])
        
        # Limit number of ticks
        if 'max_xticks' in axes_kwargs:
            ax.xaxis.set_major_locator(plt.MaxNLocator(axes_kwargs['max_xticks']))
        elif 'max_ticks' in style:
            ax.xaxis.set_major_locator(plt.MaxNLocator(style["max_ticks"]))
            
        if 'max_yticks' in axes_kwargs:
            ax.yaxis.set_major_locator(plt.MaxNLocator(axes_kwargs['max_yticks']))
        
        # Set custom y-ticks to exclude zero
        if axes_kwargs.get('hide_y_zero', False):
            # Get current ticks
            yticks = ax.get_yticks()
            # Filter out zero (using a small threshold to handle floating point issues)
            yticks = yticks[abs(yticks) > 1e-10]
            # Apply the filtered ticks
            ax.set_yticks(yticks)
            
        # Apply custom ticks if specified
        if axes_kwargs.get('custom_xticks', False):
            if 'xticks' in axes_kwargs:
                ax.set_xticks(axes_kwargs['xticks'])
                # If you want custom tick labels, you can set them here
                if 'xtick_labels' in axes_kwargs:
                    ax.set_xticklabels(axes_kwargs['xtick_labels'])
                else:
                    # Format as integers (no decimal points)
                    ax.set_xticklabels([f"{int(x)}" for x in axes_kwargs['xticks']])
        
        # Set grid
        grid = axes_kwargs.get('grid', style["grid"])
        ax.grid(grid)
        
        # Apply scale formatter if specified
        if scale:
            self._apply_scale_formatter(ax, scale)
        
        # Add legend with potential overrides
        legend_kwargs = mpl_kwargs.get('legend', {})
        if any(label is not None for label in labels):
            legend = ax.legend(fontsize=legend_kwargs.get('fontsize', style["legend_size"]))
            
            # Apply additional legend kwargs if provided
            for key, value in legend_kwargs.items():
                if key != 'fontsize':  # Already handled above
                    try:
                        setattr(legend, f"set_{key}", value)
                    except (AttributeError, TypeError):
                        pass  # Ignore if parameter not supported
        
        # Add footer if specified
        self._add_footer(fig, metadata, style)
            
        return fig
        
    def bar_chart(self, x_data, y_data_list, metadata, stem: str) -> None:
        """Generate bar charts for both desktop and mobile."""
        # Similar implementation to line_plot but for bar charts
        # ...
        
    def waffle_chart(self, data, metadata, stem: str) -> None:
        """Generate waffle charts for both desktop and mobile."""
        # ...
    
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
    
    def _apply_scale_formatter(self, ax, scale='billions', axis='y', decimals=0, prefix='$'):
        """Apply scale formatting to axis."""
        scales = {
            'billions': {'factor': 1e9, 'suffix': 'B'},
            'millions': {'factor': 1e6, 'suffix': 'M'},
            'thousands': {'factor': 1e3, 'suffix': 'K'},
            'percentage': {'factor': 0.01, 'suffix': '%', 'prefix': ''}
        }
        
        if scale in scales:
            scale_info = scales[scale]
            factor = scale_info['factor']
            suffix = scale_info.get('suffix', '')
            prefix = scale_info.get('prefix', prefix)
            
            def formatter(x, pos):
                return f'{prefix}{x/factor:.{decimals}f}{suffix}'
                
            from matplotlib.ticker import FuncFormatter
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
            color = self.COLORS["medium_gray"]
        
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
            
            logo_path = Path(__file__).parent.parent / "img" / "TPS_Logo_1Line-Black.png"
            if not logo_path.exists():
                return
                
            logo = mpimg.imread(str(logo_path))
            
            # Apply color mask if the logo has an alpha channel (RGBA)
            if logo.shape[2] == 4:  # RGBA format
                # Extract alpha channel
                alpha = logo[:, :, 3]
                
                # Create a color mask for the logo to better
                # match the chart colors
                hex_color = self.COLORS["lunar_dust"]
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
            color=self.COLORS["lunar_dust"],
            ha='left',
            va='bottom'
        )
    
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