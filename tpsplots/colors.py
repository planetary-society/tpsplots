"""TPS brand color palette definitions and color utilities.

This module provides the canonical color definitions for all TPS charts.
Import from here rather than from views to avoid circular dependencies
and maintain proper separation between data/controller and view layers.

Usage:
    from tpsplots.colors import COLORS, TPS_COLORS, lighten_color

    # Accessibility-first colors (short names)
    blue = COLORS["blue"]  # "#037CC2"

    # Brand colors (full names)
    neptune = TPS_COLORS["Neptune Blue"]  # "#037CC2"
"""

# Accessibility-first color palette with short, semantic names.
# These meet WCAG contrast requirements on typical chart backgrounds.
COLORS: dict[str, str] = {
    "blue": "#037CC2",
    "purple": "#643788",
    "orange": "#FF5D47",
    "light_blue": "#3696CE",  # minimum for AA contrast on grey background
    "light_purple": "#9C83B4",  # minimum for AA contrast on grey background
    "lunar_dust": "#8C8C8C",  # meets minimum for graphics but not for text against grey background
    "dark_gray": "#414141",
    "medium_gray": "#C3C3C3",
    "light_gray": "#F5F5F5",
}

# TPS brand color palette with official naming.
# Use these when brand consistency is more important than brevity.
TPS_COLORS: dict[str, str] = {
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


def lighten_color(color: str, factor: float = 0.4) -> str:
    """Lighten a hex color by blending it with white.

    Args:
        color: Hex color string (e.g., "#037CC2")
        factor: Amount to lighten (0=no change, 1=white)

    Returns:
        Lightened hex color string, or original on parse failure.
    """
    hex_str = color.lstrip("#")
    try:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        return color
