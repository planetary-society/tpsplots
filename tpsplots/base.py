"""tpsplots.base – shared chart infrastructure"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple, Dict
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.util import Inches

# ------------------------------------------------------------------#
# Load TPS house style *once* at import time
plt.style.use(Path(__file__).parent / "style" / "tps.mplstyle")

class BaseChart:
    """Parent for all TPS charts: common style + export helpers."""

    # aspect-ratio presets
    RATIOS: Dict[str, Tuple[int, int]] = {"16x9": (16, 9), "1x1": (10, 10)}

    def __init__(self, data_source=None, outdir: str | os.PathLike = "charts"):
        self.data_source = data_source
        self.outdir = Path(outdir)

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