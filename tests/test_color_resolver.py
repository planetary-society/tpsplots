"""Tests for ColorResolver."""

from tpsplots.processors.resolvers import ColorResolver


class TestColorResolver:
    """Test color name resolution with exact matching."""

    def test_colors_dict_names(self):
        """COLORS keys resolve correctly."""
        assert ColorResolver.resolve("blue") == "#037CC2"
        assert ColorResolver.resolve("purple") == "#643788"
        assert ColorResolver.resolve("orange") == "#FF5D47"
        assert ColorResolver.resolve("light_blue") == "#3696CE"

    def test_tps_colors_spaced_names(self):
        """TPS_COLORS keys with spaces resolve."""
        assert ColorResolver.resolve("Neptune Blue") == "#037CC2"
        assert ColorResolver.resolve("Rocket Flame") == "#FF5D47"
        assert ColorResolver.resolve("Plasma Purple") == "#643788"
        assert ColorResolver.resolve("Lunar Soil") == "#8C8C8C"

    def test_hex_passthrough(self):
        """Hex codes pass through unchanged."""
        assert ColorResolver.resolve("#037CC2") == "#037CC2"
        assert ColorResolver.resolve("#FF5D47") == "#FF5D47"

    def test_template_passthrough(self):
        """Template references pass through unchanged."""
        assert ColorResolver.resolve("{{colors}}") == "{{colors}}"

    def test_list_resolution(self):
        """Lists of colors resolve each element."""
        result = ColorResolver.resolve(["blue", "Neptune Blue", "#FF5D47"])
        assert result == ["#037CC2", "#037CC2", "#FF5D47"]

    def test_none_returns_none(self):
        """None input returns None."""
        assert ColorResolver.resolve(None) is None

    def test_unknown_color_passthrough(self):
        """Unknown color names pass through unchanged (for matplotlib names)."""
        assert ColorResolver.resolve("magenta") == "magenta"
        assert ColorResolver.resolve("red") == "red"

    def test_exact_match_required(self):
        """Only exact matches work - no normalization."""
        # These should NOT resolve (wrong case/format)
        assert ColorResolver.resolve("Blue") == "Blue"  # Wrong case
        assert ColorResolver.resolve("NeptuneBlue") == "NeptuneBlue"  # No space
        assert ColorResolver.resolve("neptune blue") == "neptune blue"  # Wrong case
