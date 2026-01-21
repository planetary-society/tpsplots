"""Mixin providing TPS brand color cycling for chart views."""

from typing import ClassVar


class ColorCycleMixin:
    """
    Mixin class providing TPS brand color cycling.

    This mixin centralizes the default TPS color cycle used across multiple chart types
    including stacked bar charts, lollipop charts, and pie charts.

    Note: This mixin expects the including class to have access to:
    - self.TPS_COLORS: dict of TPS brand colors (from ChartView)
    """

    # Default TPS brand color cycle order
    TPS_COLOR_CYCLE_KEYS: ClassVar[list[str]] = [
        "Neptune Blue",
        "Plasma Purple",
        "Rocket Flame",
        "Medium Neptune",
        "Medium Plasma",
        "Crater Shadow",
    ]

    def _get_cycled_colors(self, num_items, colors=None):
        """
        Get colors for a specified number of items, cycling through available colors.

        Args:
            num_items: Number of items that need colors
            colors: Optional custom color list. If provided, cycles through this list.
                   Can be a single color string, list of colors, or None for defaults.

        Returns:
            List of hex color strings, one per item. Colors cycle if fewer colors
            than items are provided.

        Examples:
            >>> mixin._get_cycled_colors(3)
            ['#037CC2', '#643788', '#FF5D47']  # First 3 TPS colors

            >>> mixin._get_cycled_colors(3, colors="#FF0000")
            ['#FF0000', '#FF0000', '#FF0000']  # Single color repeated

            >>> mixin._get_cycled_colors(5, colors=["#AA", "#BB"])
            ['#AA', '#BB', '#AA', '#BB', '#AA']  # Colors cycle
        """
        if num_items <= 0:
            return []

        if colors is None:
            # Use default TPS color cycle
            color_cycle = [self.TPS_COLORS[key] for key in self.TPS_COLOR_CYCLE_KEYS]
        elif isinstance(colors, str):
            # Single color - repeat for all items
            return [colors] * num_items
        elif isinstance(colors, (list, tuple)):
            color_cycle = list(colors)
        else:
            # Fallback to default TPS colors for unknown types
            color_cycle = [self.TPS_COLORS[key] for key in self.TPS_COLOR_CYCLE_KEYS]

        # Cycle through colors to fill all items
        return [color_cycle[i % len(color_cycle)] for i in range(num_items)]
