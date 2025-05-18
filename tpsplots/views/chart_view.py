"""Base chart generation view component with desktop/mobile versions built in."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from matplotlib.ticker import FuncFormatter
import warnings
from tpsplots import TPS_STYLE_FILE # custom mplstyle


class ChartView:
    """Base class for all chart views with shared functionality."""
    
    # Shared color palette
    COLORS = {
        "blue": "#037CC2",
        "purple": "#643788",
        "orange": "#FF5D47",
        "light_blue": "#3696CE", # minimum for AA contrast on grey background
        "light_purple": "#9C83B4", # minimum for AA contrast on grey background
        "lunar_dust": "#8C8C8C", # meets minimum for graphics but not for text against grey background
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
    
    def __init__(self, outdir: Path = Path("charts"), style_file=TPS_STYLE_FILE):
        """
        Initialize the chart view with output directory and style.
        
        Args:
            outdir: Output directory for chart files
            style_file: Matplotlib style file path to use
        """
        self.outdir = outdir
        self.outdir.mkdir(parents=True, exist_ok=True)
        
        # Apply style if provided
        if style_file:
            plt.style.use(style_file)
    
    def generate_chart(self, metadata, stem, **kwargs):
        """
        Generate desktop and mobile versions of a chart.
        
        Args:
            metadata: Chart metadata dictionary
            stem: Base filename for the chart
            **kwargs: Additional parameters for chart creation
            
        Returns:
            dict: Dictionary with desktop and mobile figure objects
        """
        # Create desktop version
        desktop_kwargs = kwargs.copy()
        desktop_kwargs['style'] = self.DESKTOP
        desktop_fig = self._create_chart(metadata, **desktop_kwargs)
        self._save_chart(desktop_fig, f"{stem}_desktop", create_pptx=True)
        
        # Create mobile version
        mobile_kwargs = kwargs.copy()
        mobile_kwargs['style'] = self.MOBILE
        mobile_fig = self._create_chart(metadata, **mobile_kwargs)
        self._save_chart(mobile_fig, f"{stem}_mobile", create_pptx=False)
        
        return {
            'desktop': desktop_fig,
            'mobile': mobile_fig
        }
    
    def _create_chart(self, metadata, style, **kwargs):
        """
        Abstract method to create a chart with the specified style.
        
        Args:
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            **kwargs: Additional parameters for chart creation
            
        Returns:
            matplotlib.figure.Figure: The created figure
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _create_chart")
    
    def _apply_scale_formatter(self, ax, scale='billions', axis='y', decimals=0, prefix='$'):
        """
        Apply scale formatting to axis.
        
        Args:
            ax: The matplotlib Axes object to format
            scale: Scale to apply ('billions', 'millions', 'thousands', 'percentage')
            axis: Which axis to format ('x', 'y', or 'both')
            decimals: Number of decimal places to display
            prefix: Prefix to add before the number (e.g., '$')
        """
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

        # Apply the formatter to the specified axis/axes
        if axis in ('y', 'both'):
            ax.yaxis.set_major_formatter(FuncFormatter(formatter))
        if axis in ('x', 'both'):
            ax.xaxis.set_major_formatter(FuncFormatter(formatter))
    
    def _add_footer(self, fig, metadata, style, bottom_margin=0.1):
        """
        Add footer elements to the figure: horizontal line, source text, and logo.
        
        Args:
            fig: The matplotlib Figure object
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            bottom_margin: Bottom margin to reserve for the footer
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

        # Add logo if enabled in the style
        if style.get('add_logo', True):
            self._add_logo(fig)
    
    def _add_horizontal_spacer(self, fig, y_position=None, color=None, linewidth=0.5, extent=(0.02, 0.98)):
        """
        Add a horizontal line spacer to the figure.
        
        Args:
            fig: The matplotlib Figure object
            y_position: Y-position of the line in figure coordinates
            color: Color of the line
            linewidth: Width of the line
            extent: Tuple of (start, end) x-positions in figure coordinates
        """
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
        """
        Add The Planetary Society logo to the figure.
        
        Args:
            fig: The matplotlib Figure object
        """
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
        """
        Add source text to the bottom left of the figure.
        
        Args:
            fig: The matplotlib Figure object
            source_text: Source text to display
        """
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
        """
        Save chart as SVG, PNG, and optionally PPTX.
        
        Args:
            fig: The matplotlib Figure object
            filename: Base filename for saving
            create_pptx: Whether to create a PowerPoint file
        """
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
        """
        Create a PowerPoint file with the chart.
        
        Args:
            png_path: Path to the PNG image to include
            pptx_path: Path for the output PowerPoint file
        """
        from pptx import Presentation
        from pptx.util import Inches
        
        prs = Presentation()
        
        # Set slide size to 16x9
        prs.slide_width = Inches(13.33)  # 16 inches wide
        prs.slide_height = Inches(7.5)  # 9 inches tall
        
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        slide.shapes.add_picture(str(png_path), Inches(0.5), Inches(0.5), width=Inches(12.33))
        prs.save(pptx_path)