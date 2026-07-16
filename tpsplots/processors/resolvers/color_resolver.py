"""Color name resolver for semantic color names to hex codes."""

from typing import Any, ClassVar

from tpsplots.colors import resolve_color


class ColorResolver:
    """Resolves semantic color names to hex codes using case-insensitive matching.

    Supports:
    - COLORS keys: "blue", "purple", "orange" (accessibility-first)
    - TPS_COLORS keys: "Neptune Blue", "Rocket Flame" (brand colors)
    - Hex passthrough: "#037CC2" → "#037CC2"
    - List handling: ["blue", "Neptune Blue"] → ["#037CC2", "#037CC2"]
    - Deep resolution: Recursively resolves colors in nested structures

    COLORS takes precedence over TPS_COLORS when keys conflict. The single-value
    lookup is delegated to :func:`tpsplots.colors.resolve_color`.
    """

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
        """Resolve a single color value (delegates to ``colors.resolve_color``)."""
        return resolve_color(value)

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
