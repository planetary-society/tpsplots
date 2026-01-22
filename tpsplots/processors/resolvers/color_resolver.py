"""Color name resolver for semantic color names to hex codes."""

from tpsplots.views.chart_view import ChartView


class ColorResolver:
    """Resolves semantic color names to hex codes using exact string matching.

    Supports:
    - COLORS keys: "blue", "purple", "orange" (accessibility-first)
    - TPS_COLORS keys: "Neptune Blue", "Rocket Flame" (brand colors)
    - Hex passthrough: "#037CC2" → "#037CC2"
    - List handling: ["blue", "Neptune Blue"] → ["#037CC2", "#037CC2"]

    COLORS takes precedence over TPS_COLORS when keys conflict.
    """

    # Build unified lookup map (COLORS takes precedence for accessibility)
    _COLOR_MAP: dict[str, str] = {}

    @classmethod
    def _build_color_map(cls) -> dict[str, str]:
        """Build color lookup map with exact string keys."""
        if cls._COLOR_MAP:
            return cls._COLOR_MAP

        # Add TPS_COLORS first (lower precedence)
        cls._COLOR_MAP.update(ChartView.TPS_COLORS)

        # Add COLORS second (higher precedence, overwrites conflicts)
        cls._COLOR_MAP.update(ChartView.COLORS)

        return cls._COLOR_MAP

    @classmethod
    def resolve(cls, value):
        """Resolve color value(s) to hex code(s).

        Args:
            value: String, list of strings, or None

        Returns:
            Resolved hex code(s), or original value if not resolvable
        """
        if value is None:
            return None

        if isinstance(value, list):
            return [cls._resolve_single(v) for v in value]

        return cls._resolve_single(value)

    @classmethod
    def _resolve_single(cls, value: str) -> str:
        """Resolve a single color value."""
        if not isinstance(value, str):
            return value

        # Skip template references like {{colors}}
        if value.startswith("{{") and value.endswith("}}"):
            return value

        # Skip hex codes
        if value.startswith("#"):
            return value

        # Exact match lookup in color map
        color_map = cls._build_color_map()
        return color_map.get(value, value)  # Return original if not found
