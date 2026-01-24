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


class TestColorResolverDeep:
    """Test deep/recursive color resolution."""

    def test_flat_dict_with_colors(self):
        """Top-level colors field in dict is resolved."""
        data = {"colors": ["Neptune Blue", "Rocket Flame"], "other": "value"}
        result = ColorResolver.resolve_deep(data)
        assert result == {"colors": ["#037CC2", "#FF5D47"], "other": "value"}

    def test_nested_dict_with_colors(self):
        """Nested colors field is resolved."""
        data = {"subplot_data": [{"title": "Test", "colors": ["Neptune Blue", "Rocket Flame"]}]}
        result = ColorResolver.resolve_deep(data)
        assert result["subplot_data"][0]["colors"] == ["#037CC2", "#FF5D47"]

    def test_deeply_nested_colors(self):
        """Colors at any depth are resolved."""
        data = {"level1": {"level2": {"level3": {"colors": "blue"}}}}
        result = ColorResolver.resolve_deep(data)
        assert result["level1"]["level2"]["level3"]["colors"] == "#037CC2"

    def test_multiple_color_fields(self):
        """Different color field names all resolved."""
        data = {
            "color": "Neptune Blue",
            "positive_color": "Rocket Flame",
            "edgecolor": "Plasma Purple",
        }
        result = ColorResolver.resolve_deep(data)
        assert result["color"] == "#037CC2"
        assert result["positive_color"] == "#FF5D47"
        assert result["edgecolor"] == "#643788"

    def test_non_color_fields_unchanged(self):
        """Fields not in COLOR_FIELDS pass through unchanged."""
        data = {"title": "Neptune Blue", "xlabel": "Rocket Flame"}
        result = ColorResolver.resolve_deep(data)
        assert result["title"] == "Neptune Blue"  # Not resolved
        assert result["xlabel"] == "Rocket Flame"  # Not resolved

    def test_non_container_passthrough(self):
        """Non-dict/list values pass through unchanged."""
        assert ColorResolver.resolve_deep("Neptune Blue") == "Neptune Blue"
        assert ColorResolver.resolve_deep(123) == 123
        assert ColorResolver.resolve_deep(None) is None

    def test_mixed_nested_structure(self):
        """Complex nested structure with multiple color fields at different levels."""
        data = {
            "colors": ["blue", "orange"],
            "subplot_data": [
                {
                    "title": "Sub 1",
                    "colors": ["Neptune Blue"],
                    "nested": {"edgecolor": "Plasma Purple"},
                },
                {
                    "title": "Sub 2",
                    "positive_color": "blue",
                    "negative_color": "orange",
                },
            ],
            "metadata": {"author": "Test"},
        }
        result = ColorResolver.resolve_deep(data)
        assert result["colors"] == ["#037CC2", "#FF5D47"]
        assert result["subplot_data"][0]["colors"] == ["#037CC2"]
        assert result["subplot_data"][0]["nested"]["edgecolor"] == "#643788"
        assert result["subplot_data"][1]["positive_color"] == "#037CC2"  # blue -> COLORS
        assert result["subplot_data"][1]["negative_color"] == "#FF5D47"
        assert result["metadata"]["author"] == "Test"
