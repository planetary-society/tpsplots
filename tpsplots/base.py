"""tpsplots.base – shared chart infrastructure"""
from __future__ import annotations
from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Tuple, Dict
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pptx import Presentation
from pptx.util import Inches

from styles import ChartStyle, ChartStyleFactory

# ------------------------------------------------------------------#
# Load TPS chart styles
plt.style.use(Path(__file__).parent / "style" / "tps.mplstyle")

class BaseChart(ABC):
    """Parent for all TPS charts: common style + export helpers."""

    # aspect-ratio presets
    RATIOS: Dict[str, Tuple[int, int]] = {"16x9": (16, 9), "1x1": (10, 10)}

    # TPS Brand colors
    COLORS = {
        "blue": "#037CC2",
        "purple": "#643788",
        "orange": "#FF5D47",
        "light_blue": "#80BDE0",
        "light_purple": "#B19BC3",
        "dark_gray": "#414141",
        "medium_gray": "#C3C3C3",
        "light_gray": "#F5F5F5"
    }

    def __init__(self, data_source=None, outdir: str | os.PathLike = "charts"):
        self.data_source = data_source
        self.outdir = Path(outdir)


    def apply_scale_formatter(self, ax, scale='billions', axis='y', decimals=1, prefix='$', suffix=None):
        """
        Format axis values with a scale factor, custom prefix and suffix.
        
        Args:
            ax: The matplotlib axis to format
            scale: Scale to use ('billions', 'millions', 'thousands', 'percentage', or numeric scale factor)
            axis: Which axis to format ('x', 'y', or 'both')
            decimals: Number of decimal places to show
            prefix: String prefix (e.g. '$')
            suffix: String suffix override (if None, uses default for scale)
        """
        # Set up scale-specific parameters
        scale_info = {
            'billions': {'factor': 1e9, 'default_suffix': 'B'},
            'millions': {'factor': 1e6, 'default_suffix': 'M'},
            'thousands': {'factor': 1e3, 'default_suffix': 'K'},
            'percentage': {'factor': 0.01, 'default_suffix': '%', 'prefix': ''}
        }
        
        # Get scale parameters or use custom scale factor
        if isinstance(scale, str) and scale.lower() in scale_info:
            scale_data = scale_info[scale.lower()]
            factor = scale_data['factor']
            # Use provided suffix or default for this scale
            suffix = suffix if suffix is not None else scale_data['default_suffix']
            # For percentage, override prefix if not explicitly provided
            if scale.lower() == 'percentage' and prefix == '$':
                prefix = scale_data.get('prefix', '')
        else:
            # Assume scale is a numeric scale factor
            try:
                factor = float(scale)
                suffix = suffix if suffix is not None else ''
            except (ValueError, TypeError):
                raise ValueError(f"Unknown scale: {scale}. Use 'billions', 'millions', 'thousands', "
                                f"'percentage', or a numeric scale factor.")
        
        # Create the formatter function
        def formatter(x, pos):
            if scale.lower() == 'percentage':
                # For percentage, we multiply by 100
                return f'{x*100:.{decimals}f}{suffix}'
            else:
                # For other scales, we divide by the factor
                return f'{prefix}{x/factor:.{decimals}f}{suffix}'
        
        # Apply the formatter to the specified axes
        fmt = FuncFormatter(formatter)
        
        if axis.lower() in ('y', 'both'):
            ax.yaxis.set_major_formatter(fmt)
        
        if axis.lower() in ('x', 'both'):
            ax.xaxis.set_major_formatter(fmt)

    # Convenience methods that call the unified formatter
    def apply_billions_formatter(self, ax, axis='y', decimals=1, prefix='$', suffix='B'):
        """Format axis values in billions."""
        return self.apply_scale_formatter(ax, 'billions', axis, decimals, prefix, suffix)

    def apply_millions_formatter(self, ax, axis='y', decimals=1, prefix='$', suffix='M'):
        """Format axis values in millions."""
        return self.apply_scale_formatter(ax, 'millions', axis, decimals, prefix, suffix)

    def apply_thousands_formatter(self, ax, axis='y', decimals=1, prefix='$', suffix='K'):
        """Format axis values in thousands."""
        return self.apply_scale_formatter(ax, 'thousands', axis, decimals, prefix, suffix)

    def apply_percentage_formatter(self, ax, axis='y', decimals=1, prefix='', suffix='%'):
        """Format axis values as percentages."""
        return self.apply_scale_formatter(ax, 'percentage', axis, decimals, prefix, suffix)

    # -------------------- exporting ---------------------------------

    def _export(
        self,
        fig: plt.Figure,
        stem: str,
        ratios: Tuple[str, ...] = ("16x9", "1x1"),
        pptx: bool = True,
    ) -> None:
        """Save *fig* as SVG+PNG in each ratio; embed the widescreen PNG in PPTX."""
        self.outdir.mkdir(parents=True, exist_ok=True)

        for label in ratios:
            w, h = self.RATIOS[label]
            fig.set_size_inches(w, h, forward=True)
            fig.tight_layout()

            svg = self.outdir / f"{stem}_{label}.svg"
            png = self.outdir / f"{stem}_{label}.png"
            fig.savefig(svg, format="svg", bbox_inches="tight")
            fig.savefig(png, format="png", dpi=300, bbox_inches="tight")
            print(f"✓ saved {svg.name} and {png.name}")

            if pptx and label == "16x9":
                self._png_to_pptx(png, self.outdir / f"{stem}.pptx")

        plt.close(fig)

    @staticmethod
    def _png_to_pptx(png_path: Path, pptx_path: Path) -> None:
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        slide.shapes.add_picture(str(png_path), Inches(0.5), Inches(0.5), width=Inches(9))
        prs.save(pptx_path)