"""Unit tests for ColorCycleMixin.

Tests the color cycling logic used across stacked bar, lollipop, and pie charts.
"""


class TestGetCycledColors:
    """Tests for _get_cycled_colors behavior."""

    def test_returns_default_tps_colors_when_none_provided(self, mixin_with_color_cycle):
        """Default TPS brand colors are returned when no colors specified."""
        colors = mixin_with_color_cycle._get_cycled_colors(3)

        # First 3 should be Neptune Blue, Plasma Purple, Rocket Flame
        assert colors[0] == mixin_with_color_cycle.TPS_COLORS["Neptune Blue"]
        assert colors[1] == mixin_with_color_cycle.TPS_COLORS["Plasma Purple"]
        assert colors[2] == mixin_with_color_cycle.TPS_COLORS["Rocket Flame"]

    def test_single_color_repeated_for_all_items(self, mixin_with_color_cycle):
        """Single color string is repeated for all items."""
        colors = mixin_with_color_cycle._get_cycled_colors(5, colors="#FF0000")

        assert colors == ["#FF0000", "#FF0000", "#FF0000", "#FF0000", "#FF0000"]

    def test_color_list_cycles_when_fewer_than_items(self, mixin_with_color_cycle):
        """Colors cycle when list is shorter than num_items."""
        colors = mixin_with_color_cycle._get_cycled_colors(5, colors=["#AA", "#BB"])

        assert colors == ["#AA", "#BB", "#AA", "#BB", "#AA"]

    def test_color_list_truncated_when_more_than_items(self, mixin_with_color_cycle):
        """Full list used when longer than num_items (extras cycle anyway)."""
        colors = mixin_with_color_cycle._get_cycled_colors(2, colors=["#AA", "#BB", "#CC", "#DD"])

        assert colors == ["#AA", "#BB"]

    def test_empty_list_returns_empty(self, mixin_with_color_cycle):
        """Zero items returns empty list."""
        colors = mixin_with_color_cycle._get_cycled_colors(0)

        assert colors == []

    def test_negative_items_returns_empty(self, mixin_with_color_cycle):
        """Negative num_items returns empty list."""
        colors = mixin_with_color_cycle._get_cycled_colors(-5)

        assert colors == []

    def test_tuple_colors_work_like_list(self, mixin_with_color_cycle):
        """Tuple of colors works same as list."""
        colors = mixin_with_color_cycle._get_cycled_colors(3, colors=("#AA", "#BB"))

        assert colors == ["#AA", "#BB", "#AA"]

    def test_unknown_type_falls_back_to_defaults(self, mixin_with_color_cycle):
        """Invalid color type falls back to TPS defaults."""
        colors = mixin_with_color_cycle._get_cycled_colors(2, colors=12345)

        # Should get first two TPS colors
        assert colors[0] == mixin_with_color_cycle.TPS_COLORS["Neptune Blue"]
        assert colors[1] == mixin_with_color_cycle.TPS_COLORS["Plasma Purple"]

    def test_full_cycle_wraps_correctly(self, mixin_with_color_cycle):
        """Requesting more items than default colors cycles properly."""
        # Default has 6 colors, request 8
        colors = mixin_with_color_cycle._get_cycled_colors(8)

        # 7th and 8th should wrap to 1st and 2nd
        assert colors[6] == colors[0]  # Neptune Blue
        assert colors[7] == colors[1]  # Plasma Purple


class TestMixinIntegration:
    """Tests for mixin integration with chart views."""

    def test_stacked_bar_chart_has_cycled_colors(self):
        """StackedBarChartView has access to _get_cycled_colors."""
        from tpsplots.views.stacked_bar_chart import StackedBarChartView

        view = StackedBarChartView()
        assert hasattr(view, "_get_cycled_colors")

        colors = view._get_cycled_colors(3)
        assert len(colors) == 3

    def test_lollipop_chart_has_cycled_colors(self):
        """LollipopChartView has access to _get_cycled_colors."""
        from tpsplots.views.lollipop_chart import LollipopChartView

        view = LollipopChartView()
        assert hasattr(view, "_get_cycled_colors")

        colors = view._get_cycled_colors(3)
        assert len(colors) == 3

    def test_us_map_pie_chart_has_cycled_colors(self):
        """USMapPieChartView has access to _get_cycled_colors."""
        from tpsplots.views.us_map_pie_charts import USMapPieChartView

        view = USMapPieChartView()
        assert hasattr(view, "_get_cycled_colors")

        colors = view._get_cycled_colors(3)
        assert len(colors) == 3

    def test_color_cycle_keys_match_tps_colors(self):
        """TPS_COLOR_CYCLE_KEYS all exist in TPS_COLORS."""
        from tpsplots.views.mixins import ColorCycleMixin
        from tpsplots.views.stacked_bar_chart import StackedBarChartView

        view = StackedBarChartView()

        for key in ColorCycleMixin.TPS_COLOR_CYCLE_KEYS:
            assert key in view.TPS_COLORS, f"Missing color key: {key}"
