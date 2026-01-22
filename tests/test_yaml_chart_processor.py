"""Tests for YAMLChartProcessor.

Tests focus on:
- Bug 5: All color parameters should be resolved from semantic names
"""


class TestColorParameterResolution:
    """Tests for color parameter resolution completeness - Bug 5 fix."""

    # This is the list of color params that SHOULD be resolved
    # If any of these are missing from the processor, semantic colors won't work
    EXPECTED_COLOR_PARAMS = [
        # Original 8 params
        "color",
        "colors",
        "positive_color",
        "negative_color",
        "value_color",
        "center_color",
        "end_marker_color",
        "offset_line_color",
        # Missing params (Bug 5)
        "start_marker_color",
        "start_marker_edgecolor",
        "end_marker_edgecolor",
        "line_colors",
        "hline_colors",
        "edgecolor",
        "y_tick_color",
        "pie_edge_color",
    ]

    def test_color_params_list_is_complete(self):
        """Verify all expected color params are in the processor's list."""
        # Import here to avoid circular dependencies
        import inspect

        from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

        # Get the source of the generate_chart method
        source = inspect.getsource(YAMLChartProcessor.generate_chart)

        # Check that each expected param is mentioned in the color_params list
        # This is a bit fragile but catches the exact bug
        for param in self.EXPECTED_COLOR_PARAMS:
            assert f'"{param}"' in source, (
                f"Color param '{param}' not found in YAMLChartProcessor.generate_chart(). "
                f"Users using semantic color names for {param} will get errors."
            )

    def test_color_resolution_handles_lists(self):
        """Color params that accept lists should resolve each item."""
        from tpsplots.processors.resolvers import ColorResolver

        # Test list of semantic colors
        colors = ["Neptune Blue", "Rocket Flame", "Plasma Purple"]
        resolved = ColorResolver.resolve(colors)

        assert resolved == ["#037CC2", "#FF5D47", "#643788"]

    def test_color_resolution_handles_single_values(self):
        """Color params that accept single values should resolve correctly."""
        from tpsplots.processors.resolvers import ColorResolver

        color = "Neptune Blue"
        resolved = ColorResolver.resolve(color)

        assert resolved == "#037CC2"

    def test_color_resolution_passes_through_hex(self):
        """Hex colors should pass through unchanged."""
        from tpsplots.processors.resolvers import ColorResolver

        hex_color = "#FF0000"
        resolved = ColorResolver.resolve(hex_color)

        assert resolved == "#FF0000"

    def test_color_resolution_passes_through_named_colors(self):
        """Standard matplotlib color names should pass through."""
        from tpsplots.processors.resolvers import ColorResolver

        named_color = "red"
        resolved = ColorResolver.resolve(named_color)

        # Non-TPS colors pass through unchanged
        assert resolved == "red"
