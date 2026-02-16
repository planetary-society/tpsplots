"""Color name resolver for semantic color names to hex codes."""

from typing import Any, ClassVar

from tpsplots.colors import COLORS, TPS_COLORS


class ColorResolver:
    """Resolves semantic color names to hex codes using case-insensitive matching.

    Supports:
    - COLORS keys: "blue", "purple", "orange" (accessibility-first)
    - TPS_COLORS keys: "Neptune Blue", "Rocket Flame" (brand colors)
    - Hex passthrough: "#037CC2" → "#037CC2"
    - List handling: ["blue", "Neptune Blue"] → ["#037CC2", "#037CC2"]
    - Deep resolution: Recursively resolves colors in nested structures

    COLORS takes precedence over TPS_COLORS when keys conflict.
    """

    # Build unified lookup map (COLORS takes precedence for accessibility)
    _COLOR_MAP: ClassVar[dict[str, str]] = {}
    _NORMALIZED_COLOR_MAP: ClassVar[dict[str, str]] = {}

    # Color field names that should be resolved when encountered in dicts
    COLOR_FIELDS: ClassVar[set[str]] = {
        "color",
        "colors",
        "positive_color",
        "negative_color",
        "value_color",
        "center_color",
        "start_marker_color",
        "end_marker_color",
        "start_marker_edgecolor",
        "end_marker_edgecolor",
        "y_tick_color",
        "line_colors",
        "hline_colors",
        "edgecolor",
        "pie_edge_color",
        "offset_line_color",
    }

    @classmethod
    def _build_color_map(cls) -> dict[str, str]:
        """Build color lookup maps with exact and normalized keys."""
        if cls._COLOR_MAP:
            return cls._COLOR_MAP

        # Add TPS_COLORS first (lower precedence)
        cls._COLOR_MAP.update(TPS_COLORS)

        # Add COLORS second (higher precedence, overwrites conflicts)
        cls._COLOR_MAP.update(COLORS)

        cls._NORMALIZED_COLOR_MAP = {
            cls._normalize_color_name(key): value for key, value in cls._COLOR_MAP.items()
        }

        return cls._COLOR_MAP

    @staticmethod
    def _normalize_color_name(value: str) -> str:
        """Normalize color names for case-insensitive lookup."""
        return value.strip().casefold()

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
        if value in color_map:
            return color_map[value]

        normalized_value = cls._normalize_color_name(value)
        return cls._NORMALIZED_COLOR_MAP.get(normalized_value, value)

    @classmethod
    def resolve_deep(cls, value: Any) -> Any:
        """Recursively resolve colors in any nested structure.

        Walks through dicts and lists, resolving values in color-named fields.
        Non-color fields are recursively traversed but their values are not resolved.

        Args:
            value: Any value - dict, list, or scalar

        Returns:
            The same structure with color fields resolved to hex codes
        """
        if isinstance(value, dict):
            return {
                k: cls.resolve(v) if k in cls.COLOR_FIELDS else cls.resolve_deep(v)
                for k, v in value.items()
            }

        if isinstance(value, list):
            return [cls.resolve_deep(item) for item in value]

        # Non-container values pass through unchanged
        return value
