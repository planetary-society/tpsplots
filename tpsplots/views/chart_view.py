"""Base chart generation view component with desktop/mobile versions built in."""
from pathlib import Path
from datetime import datetime
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates
import warnings
import logging
import textwrap
from typing import Optional

from tpsplots import TPS_STYLE_FILE # custom mplstyle

logger = logging.getLogger(__name__)

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
        "type": "desktop",
        "figsize": (16, 10),
        "dpi": 300,
        "title_size": 26,
        "label_size": 20,
        "tick_size": 20,
        "legend_size": 18,
        "line_width": 4,
        "marker_size": 6,
        "grid": True,
        "grid_axis": "both",
        "tick_rotation": 0,
        "add_logo": True,
        "max_ticks": 25,
        "footer": True,
        "footer_height": 0.08,
        "header": True,
        "header_height": 0.1,
        "subtitle_offset": 0.93, # y position of subtitle
        "subtitle_wrap_length": 120,
        "label_wrap_length": 30
    }
    
    MOBILE = {
        "type": "mobile",
        "figsize": (8, 9),
        "dpi": 300,
        "title_size": 24,
        "label_size": 20,
        "tick_size": 20,
        "legend_size": 15,
        "line_width": 4,
        "marker_size": 5,
        "grid": True,
        "grid_axis": "y",
        "tick_rotation": 90,
        "add_logo": True,
        "footer": True,
        "footer_height": 0.08,
        "header": True,
        "header_height": 0.14,
        "subtitle_offset": 0.93,
        "subtitle_wrap_length": 64,
        "label_wrap_length": 15
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
            export: dataframe to export to CSV
            **kwargs: Additional parameters for chart creation
            
        Returns:
            dict: Dictionary with desktop and mobile figure objects
        """
        
        export_data = kwargs.pop("export_data", None)
        
        # Create desktop version
        desktop_kwargs = kwargs.copy()
        desktop_kwargs['style'] = self.DESKTOP
        desktop_fig = self._create_chart(metadata, **desktop_kwargs)
        self._save_chart(desktop_fig, f"{stem}_desktop", metadata, create_pptx=True)
        
        # Create mobile version
        mobile_kwargs = kwargs.copy()
        mobile_kwargs['style'] = self.MOBILE
        mobile_fig = self._create_chart(metadata, **mobile_kwargs)
        self._save_chart(mobile_fig, f"{stem}_mobile", metadata, create_pptx=False)
        
        # Export CSV if export_data is present
        if export_data is not None:
            self._export_csv(export_data,metadata,stem)
        
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
    
    def _export_csv(self, df, metadata, stem):
        """
        Export chart data as CSV with metadata header rows.
        
        Args:
            df: The pandas DataFrame containing the chart data
            metadata: Chart metadata dictionary
            stem: Base filename for saving
        """
        csv_path = self.outdir / f"{stem}.csv"
        
        # Create a copy of the data to avoid modifying the original
        csv_df = df.copy()
        
        # Prepare metadata rows
        meta_rows = []
        
        # Add author and generation info
        meta_rows.append(["Author", "Casey Dreier/The Planetary Society"])
        meta_rows.append(["Website", "https://planetary.org"])
        meta_rows.append(["Generated", datetime.now().strftime("%Y-%m-%d")])
        
        if 'source' in metadata:
            meta_rows.append(["Data Source", metadata['source']])
        meta_rows.append(["License","CC BY 4.0"])
        
        # Add a blank row between metadata and data
        meta_rows.append(["",""])
        
        # Write metadata and data to CSV
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write metadata rows
            for row in meta_rows:
                writer.writerow(row)
            
            # Write column names and data, converting NaN to empty strings
            writer.writerow(csv_df.columns)
            for _, row in csv_df.iterrows():
                # Convert each value: if it's NaN, write '', else write the value
                writer.writerow(['' if (isinstance(val, float) and np.isnan(val)) else val for val in row])
        
        logger.info(f"✓ saved {csv_path.name}")
        return csv_path
    
    def _apply_fiscal_year_ticks(self, ax, style, tick_size=None):
        """
        Apply consistent fiscal year tick formatting to the x-axis.
        
        Sets major ticks at decade boundaries (years ending in 0),
        minor ticks at each year, and formats all labels horizontally.
        
        Args:
            ax: Matplotlib axes object
            style: dict of MOBILE or DESKTOP style options
            tick_size: Optional font size for tick labels
        """
       
        # Set major ticks at decade boundaries (years divisible by 10)
        ax.xaxis.set_major_locator(mdates.YearLocator(5))  # Every 5 years
        ax.xaxis.set_minor_locator(mdates.YearLocator(1))   # Every year

        # Format to show only the year
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

        # Only apply decade_label if x-axis range is greater than 20 years
        xlim = ax.get_xlim()
        try:
            start_year = mdates.num2date(xlim[0]).year
            end_year = mdates.num2date(xlim[1]).year
            year_range = abs(end_year - start_year)
        except Exception:
            year_range = 0

        # if the range is greater than 20 years, show only decade labels
        if year_range > 20:
            def decade_label(year, pos):
                year_int = int(mdates.num2date(year).year)
                return str(year_int) if year_int % 10 == 0 else ""
            ax.xaxis.set_major_formatter(FuncFormatter(decade_label))
        elif year_range < 10:
            # If the range is less than 10 years, show all years
            ax.xaxis.set_major_locator(mdates.YearLocator(1))


        # Make minor ticks visible but unlabeled
        ax.tick_params(which='minor', length=4, color='gray', width=1)
        ax.tick_params(which='major', length=8, width=1.2)

        # Allow override on tick size
        if tick_size is None:
            tick_size = style.get("tick_size")

        # Set tick labels horizontal and apply font size if provided
        plt.setp(ax.get_xticklabels(), rotation=style.get("tick_rotation",0), fontsize=tick_size)
        
        return ax

    # Helper to detect if x_data contains dates
    def _contains_dates(self, x_data):
        """
        Check if x_data contains date-like objects.
        
        Args:
            x_data: The x-axis data to check
            
        Returns:
            bool: True if the data appears to contain dates
        """
        if x_data is None or len(x_data) == 0:
            return False
            
        # Check if x_data contains datetime objects
        try:
            first_elem = x_data.iloc[0] if hasattr(x_data, "iloc") else x_data[0]
        except KeyError as e:
            logger.warning(f"Cannot read first element in array to check date objects: {x_data}")
            return False
        
        # Check for datetime-like objects
        if hasattr(first_elem, 'year') and hasattr(first_elem, 'month'):
            return True
            
        # Check for numpy datetime64
        if hasattr(first_elem, 'dtype') and np.issubdtype(first_elem.dtype, np.datetime64):
            return True
            
        # Check for integer years (1980, 1990, etc.)
        if isinstance(first_elem, int) and 1900 <= first_elem <= 2100:
            return True
            
        # Check for string years ("1980", "1990", etc.)
        if isinstance(first_elem, str) and first_elem.isdigit() and 1900 <= int(first_elem) <= 2100:
            return True
            
        return False
    
    def _apply_scale_formatter(self, ax, scale :str ='billions', axis :str = 'y', decimals: Optional[int] = None, prefix :Optional[str] = '$'):
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
            return
        
        scale_info = scales[scale]
        factor = scale_info['factor']
        suffix = scale_info.get('suffix', '')
        prefix = scale_info.get('prefix', prefix)
        
        # Determine the number of decimals for smaller scales
        if decimals is None and axis in ('y', 'both'):
            ylim = ax.get_ylim()
            try:
                range_value = (abs(ylim[1] - ylim[0]))/factor
                if range_value < 10:
                    decimals = 1
                else:
                    decimals = 0
            except Exception:
                decimals = 0

        def formatter(x, pos):
            try:
                if not np.isfinite(x):
                    return ""
                if x == 0:
                    return ""
                if factor == 0:
                    return ""
                scaled_value = x / factor
                # If range_value < 10, only show whole numbers
                if axis in ('y', 'both') and decimals == 1 and range_value < 10:
                    if not np.isclose(scaled_value, round(scaled_value)):
                        return ""
                    format_spec = '.0f'
                else:
                    format_spec = f'.{decimals}f'
                formatted_num = f'{scaled_value:{format_spec}}'
                return f'{prefix}{formatted_num}{suffix}'
            except Exception as e:
                logger.error(f"Formatter error for value x={x}, pos={pos}: {e}")
                return ""

        if axis in ('y', 'both'):
            ax.yaxis.set_major_formatter(FuncFormatter(formatter))
        if axis in ('x', 'both'):
            ax.xaxis.set_major_formatter(FuncFormatter(formatter))
    
    def _add_header(self, fig, metadata, style, top_margin=0.2):
        """
        Add header elements to the figure: title and subtitle with left alignment.
        
        Args:
            fig: The matplotlib Figure object
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            top_margin: Top margin to reserve for the header
        """
        # Check if header should be displayed
        if metadata.get('header') == False:
            return
        
        # Reserve space at the top for header
        fig.subplots_adjust(top=(1.0 - top_margin))
        
        # Add title if provided
        title = metadata.get('title')
        if title:
            fig.text(
                0.01,  # x position (left side)
                0.98,  # y position (top)
                title,
                fontsize=style["title_size"],
                fontweight='bold',
                ha='left',
                va='top'
            )
        
        # Add subtitle if provided, with word wrapping at 68 characters
        subtitle = metadata.get('subtitle')
        if subtitle:
            wrapped_subtitle = "\n".join(textwrap.wrap(self._escape_svg_text(subtitle), width=style.get("subtitle_wrap_length", 65)))
            fig.text(
            0.01,  # x position (left side)
            style.get("subtitle_offset", 0.93),  # y position (below title)
            wrapped_subtitle,
            fontsize=style["title_size"] * 0.7,
            ha='left',
            va='top'
            )


    def _add_footer(self, fig, metadata, style, bottom_margin):
        """
        Add footer elements to the figure: horizontal line, source text, and logo.
        
        Args:
            fig: The matplotlib Figure object
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE)
            bottom_margin: Bottom margin to reserve for the footer
        """
        # Check if footer should be displayed
        if metadata.get('footer') == False:
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
    
    
    def _adjust_layout_for_header_footer(self, fig, metadata, style):
        """
        Adjust figure layout to accommodate headers and footers.
        
        This method handles the spacing and layout adjustments needed for
        headers and footers, and applies tight_layout with appropriate margins.
        
        Args:
            fig: The matplotlib Figure object
            metadata: Chart metadata dictionary
            style: Style dictionary (DESKTOP or MOBILE, etc)
        """
        # Determine if header should be displayed
        show_header = style.get("header") or metadata.get("header")
        
        # Determine if footer should be displayed
        show_footer = style.get("footer") or metadata.get("footer")
        
        # Add header if enabled
        if show_header:
            self._add_header(fig, metadata, style, style["header_height"])
        
        # Add footer if enabled
        if show_footer:
            self._add_footer(fig, metadata, style, style["footer_height"])
        
        # Calculate layout bounds based on header/footer presence
        header_height = style.get("header_height", 0) if show_header else 0
        footer_height = style.get("footer_height", 0) if show_footer else 0
        
        # Apply tight layout with adjusted rectangle
        fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])
        
        return fig
    
    
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
                xy=(0.99, 0.001),  # Position at right, bottom corner
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
            logger.error(f"Warning: Could not add logo: {e}")
    
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

    def _save_chart(self, fig, filename, metadata, create_pptx=False):
        """
        Save chart as SVG, PNG, and optionally PPTX.
        
        Args:
            fig: The matplotlib Figure object
            filename: Base filename for saving
            metadata: title, source, etc context for chart
            create_pptx: Whether to create a PowerPoint file
        """
        
        clean_filename = filename.replace("_desktop","").replace("_mobile","")
        svg_path = self.outdir / f"{filename}.svg"
        png_path = self.outdir / f"{filename}.png"
        
        if "_desktop" in str(png_path):
            base_png_path = str(png_path).replace("_desktop","")
            fig.savefig(base_png_path, format="png", dpi=300)
            
        svg_metadata = {
            "Title": metadata.get("title",clean_filename.replace("_"," ")),
            "Creator": "Casey Dreier/The Planetary Society",
            "Date": datetime.today().strftime("%Y-%m-%d"),
            "Rights": "CC BY 4.0",
            "Source": metadata.get("source")
        }
        
        fig.savefig(svg_path, metadata=svg_metadata, format="svg", dpi=150)
        fig.savefig(png_path, metadata=svg_metadata, format="png", dpi=300)
        logger.info(f"✓ saved {svg_path.name} and {png_path.name}")
        
        if create_pptx:
            pptx_path = self.outdir / f"{filename.replace('_desktop','')}.pptx"
            self._create_pptx(png_path, pptx_path, metadata)
            logger.info(f"✓ saved {pptx_path.name}")
            
        plt.close(fig)

    def _create_pptx(self, png_path, pptx_path, metadata = {}):
        """
        Create a PowerPoint file with the chart, scaled by height to fit completely in a 16x9 slide.

        Args:
            png_path: Path to the PNG image to include
            pptx_path: Path for the output PowerPoint file
        """
        from pptx import Presentation
        from pptx.util import Inches
        from PIL import Image
        from pptx.dml.color import RGBColor

        prs = Presentation()
        # Set slide size to 16x9 (in inches)
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(7.5)

        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

        # Set slide background color to self.TPS_COLORS['Slushy Brine']
        
        bg_color = self.TPS_COLORS['Slushy Brine']
        # Convert hex bg_color to RGB
        if isinstance(bg_color, str) and bg_color.startswith('#'):
            bg_color = bg_color.lstrip('#')
            bg_color = RGBColor(int(bg_color[0:2], 16), int(bg_color[2:4], 16), int(bg_color[4:6], 16))
        
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = bg_color

        # Get image size in inches
        with Image.open(png_path) as img:
            img_width_px, img_height_px = img.size
            img_dpi = img.info.get('dpi', (300, 300))[0]
            img_width_in = img_width_px / img_dpi
            img_height_in = img_height_px / img_dpi

        # Scale image by height to fit slide
        target_height_in = prs.slide_height / Inches(1)
        scale = target_height_in / img_height_in
        scaled_width_in = img_width_in * scale
        scaled_height_in = img_height_in * scale

        # Center the image horizontally
        left = (prs.slide_width - Inches(scaled_width_in)) / 2
        top = 0  # Top align

        slide.shapes.add_picture(
            str(png_path),
            left,
            top,
            width=Inches(scaled_width_in),
            height=Inches(scaled_height_in)
        )
        
        
        # Prepare title, subtitle, and source text
        notes = []
        notes.append(metadata.get("title"))
        notes.append(metadata.get("subtitle"))
        notes.append("\n")
        if "source" in metadata:
            notes.append("Source: " + metadata.get("source",""))
        notes.append(f"Author: {metadata.get('Creator', 'Casey Dreier/The Planetary Society')}\nGenerated: {datetime.now().strftime('%Y-%m-%d')}")
        notes.append(f"License: CC BY 4.0")

        # Clear notes of None or empty strings
        notes = [note for note in notes if note and note.strip()]
        if notes:
            # Add to text frame
            # Add title and source text to the notes section of the slide
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            text_frame.text = "\n".join(notes)
    
        # Save    
        prs.save(pptx_path)

    def _escape_svg_text(self, text):
        """
        Escape special characters for SVG text rendering in matplotlib.
        
        Args:
            text: The text string to escape
            
        Returns:
            The escaped text string
        """
        if text is None:
            return None
            
        # Define replacements for special characters
        replacements = {
            '$': r'\$'
        }
        
        # Apply all replacements
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
            
        return text