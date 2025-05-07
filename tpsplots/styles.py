from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Literal, Tuple

TPS_LOGO = Path(__file__).parent.parent / "img" / "TPS_Logo_1Line-Black.png"

# aspect-ratio presets
RATIOS: Dict[str, Tuple[int, int]] = {"desktop": (16, 9), "mobile": (10, 10)}

# TPS Brand colors
TPS_COLORS = {
    "blue": "#037CC2",
    "purple": "#643788",
    "orange": "#FF5D47",
    "light_blue": "#80BDE0",
    "light_purple": "#B19BC3",
    "dark_gray": "#414141",
    "medium_gray": "#C3C3C3",
    "light_gray": "#F5F5F5"
}

@dataclass(frozen=True, slots=True)
class ChartStyle:
    """Immutable bundle of visual parameters for a chart render."""
    name: Literal["desktop", "mobile"]
    figsize: tuple[float, float]
    dpi: int
    stylesheets: List[str]
    add_logo: bool
    logo_path: Path | None


class ChartStyleFactory:
    """Build Planetary Society chart styles from presets."""
    @staticmethod
    def make(preset: Literal["desktop", "mobile"]) -> ChartStyle:
        style_dir = Path(__file__).parent / "style"
        base_style = str(style_dir / "tps_base.mplstyle")
        
        if preset == "desktop":               # 16×9
            return ChartStyle(
                name="desktop",
                figsize=(16, 9),
                dpi=300,
                stylesheets=[base_style, str(style_dir / "tps_desktop.mplstyle")],
                add_logo=True,
                logo_path=TPS_LOGO,
            )

        if preset == "mobile":                # 1×1
            return ChartStyle(
                name="mobile",
                figsize=(8, 8),
                dpi=300,
                stylesheets=[base_style, str(style_dir / "tps_mobile.mplstyle")],
                add_logo=False,
                logo_path=None,
            )

        raise ValueError(f"Unknown style preset '{preset}'")