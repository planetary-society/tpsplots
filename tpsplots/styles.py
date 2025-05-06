from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal

TPS_LOGO = Path(__file__).parent.parent / "img" / "TPS_Logo_1Line-Black.png"

@dataclass(frozen=True, slots=True)
class ChartStyle:
    """Immutable bundle of visual parameters for a chart render."""
    name: Literal["desktop", "mobile"]
    figsize: tuple[float, float]
    dpi: int
    rc_params: Dict[str, Any]
    add_logo: bool
    logo_path: Path | None

    # Convenience proxies
    @property
    def line_width(self) -> float:
        return float(self.rc_params.get("lines.linewidth", 2.0))

    @property
    def major_tick_len(self) -> int:
        return int(self.rc_params.get("xtick.major.size", 8))

    @property
    def minor_tick_len(self) -> int | None:
        return self.rc_params.get("xtick.minor.size")  # may be None


class ChartStyleFactory:
    """Build Planetary Society chart styles from presets."""
    @staticmethod
    def make(preset: Literal["desktop", "mobile"]) -> ChartStyle:
        if preset == "desktop":               # 16×9
            return ChartStyle(
                name="desktop",
                figsize=(16, 9),
                dpi=300,
                rc_params={
                    # snippet values
                    "axes.titlesize": 20,
                    "axes.labelsize": 18,
                    "xtick.labelsize": 14,
                    "ytick.labelsize": 14,
                    "legend.fontsize": "medium",
                    "legend.title_fontsize": "medium",
                    "lines.linewidth": 2.0,
                    "lines.markersize": 8,
                },
                add_logo=True,
                logo_path=TPS_LOGO,
            )

        if preset == "mobile":                # 1×1
            return ChartStyle(
                name="mobile",
                figsize=(8, 8),
                dpi=300,
                rc_params={
                    "font.size": 14,
                    "axes.titlesize": 18,
                    "axes.labelsize": 16,
                    "xtick.labelsize": 12,
                    "ytick.labelsize": 12,
                    "legend.fontsize": 12,
                    "legend.title_fontsize": 13,
                    "lines.linewidth": 3.0,
                    "lines.markersize": 10,
                    "xtick.labelrotation": 0,
                    "ytick.labelrotation": 0,
                    "axes.grid": True,
                    "grid.linestyle": ":",
                    "grid.linewidth": 0.8,
                    "grid.alpha": 0.7,
                    "xtick.major.max_elements": 5,
                },
                add_logo=False,
                logo_path=None,
            )

        raise ValueError(f"Unknown style preset '{preset}'")