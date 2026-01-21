"""Focused unit tests for BarChartMixin methods.

Tests only meaningful logic:
- Branching logic (color determination based on values/types)
- Edge cases (empty arrays, boundary conditions)
- Business rules (positive/negative coloring, legend conditions)
- Integration (mixin works with real chart views)

Skips trivial tests:
- Simple property forwarding (ax.set_xlabel)
- Python built-ins (list multiplication)
- Matplotlib internals
"""

import numpy as np

from tests.conftest import SAMPLE_POSITIVE


class TestDetermineBarColors:
    """Tests for _determine_bar_colors branching logic."""

    def test_positive_negative_colors_assigned_by_value_sign(self, mixin):
        """Verify positive values get positive_color, negative get negative_color."""
        values = [10, -5, 20, -15]
        pos_color = "#00FF00"
        neg_color = "#FF0000"

        colors = mixin._determine_bar_colors(values, None, pos_color, neg_color)

        assert colors == ["#00FF00", "#FF0000", "#00FF00", "#FF0000"]

    def test_color_list_cycles_when_fewer_colors_than_bars(self, mixin):
        """Verify colors cycle through list when list shorter than values."""
        values = [1, 2, 3, 4, 5]
        color_list = ["#AA0000", "#00BB00"]

        colors = mixin._determine_bar_colors(values, color_list, None, None)

        # Should cycle: A, B, A, B, A
        assert colors == ["#AA0000", "#00BB00", "#AA0000", "#00BB00", "#AA0000"]

    def test_fallback_to_default_for_unknown_color_type(self, mixin):
        """Verify non-string/list colors fall back to Neptune Blue."""
        values = [1, 2, 3]
        invalid_colors = 12345  # Not a string or list

        colors = mixin._determine_bar_colors(values, invalid_colors, None, None)

        neptune_blue = mixin.TPS_COLORS["Neptune Blue"]
        assert colors == [neptune_blue, neptune_blue, neptune_blue]

    def test_empty_values_returns_empty_list(self, mixin):
        """Verify empty input doesn't crash and returns empty list."""
        colors = mixin._determine_bar_colors([], None, None, None)

        assert colors == []


class TestAddValueBasedLegend:
    """Tests for _add_value_based_legend conditional creation."""

    def test_legend_includes_both_when_mixed_values(self, mixin, ax):
        """Both Positive/Negative labels when values contain both."""
        values = [10, -5, 20]
        pos_color = "#00FF00"
        neg_color = "#FF0000"
        style = {"legend_size": 12}

        mixin._add_value_based_legend(ax, values, pos_color, neg_color, style)

        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert len(legend_texts) == 2
        assert "Positive" in legend_texts
        assert "Negative" in legend_texts

    def test_legend_omits_negative_when_all_positive(self, mixin, ax):
        """No Negative label when all values >= 0."""
        values = SAMPLE_POSITIVE  # [10, 20, 30]
        pos_color = "#00FF00"
        neg_color = "#FF0000"
        style = {"legend_size": 12}

        mixin._add_value_based_legend(ax, values, pos_color, neg_color, style)

        legend = ax.get_legend()
        assert legend is not None
        legend_texts = [t.get_text() for t in legend.get_texts()]
        assert len(legend_texts) == 1
        assert "Positive" in legend_texts
        assert "Negative" not in legend_texts

    def test_no_legend_when_neither_color_specified(self, mixin, ax):
        """No legend created without color parameters."""
        values = [10, -5]
        style = {"legend_size": 12}

        mixin._add_value_based_legend(ax, values, None, None, style)

        legend = ax.get_legend()
        assert legend is None


class TestBarValueLabels:
    """Tests for _add_bar_value_labels positioning behavior."""

    def test_labels_appear_above_positive_bars(self, mixin, ax):
        """Value labels positioned above bars for positive values."""
        values = [10, 20, 30]
        positions = np.arange(len(values))
        bars = ax.bar(positions, values)
        ax.set_ylim(0, 40)  # Set limits so offset calculation works

        mixin._add_bar_value_labels(
            ax=ax,
            bars=bars,
            values=values,
            orientation="vertical",
            value_format="integer",
            value_suffix="",
            value_offset=None,  # Auto-calculate
            fontsize=10,
            color="black",
            weight="normal",
            baseline=0,
        )

        # Get text positions
        texts = ax.texts
        assert len(texts) == 3

        # Each label should be above its bar (y > bar height)
        for i, text in enumerate(texts):
            text_y = text.get_position()[1]
            bar_height = bars[i].get_height()
            assert text_y > bar_height, f"Label {i} not above bar"

    def test_labels_appear_below_negative_bars(self, mixin, ax):
        """Value labels positioned below bars for negative values."""
        values = [-10, -20, -30]
        positions = np.arange(len(values))
        bars = ax.bar(positions, values)
        ax.set_ylim(-40, 0)  # Set limits so offset calculation works

        mixin._add_bar_value_labels(
            ax=ax,
            bars=bars,
            values=values,
            orientation="vertical",
            value_format="integer",
            value_suffix="",
            value_offset=None,
            fontsize=10,
            color="black",
            weight="normal",
            baseline=0,
        )

        texts = ax.texts
        assert len(texts) == 3

        # Each label should be below its bar (y < bar top, which is negative)
        for i, text in enumerate(texts):
            text_y = text.get_position()[1]
            bar_height = bars[i].get_height()  # Negative value
            assert text_y < bar_height, f"Label {i} not below bar"

    def test_suffix_appended_to_all_labels(self, mixin, ax):
        """Value suffix appears in all label texts."""
        values = [10, 20, 30]
        positions = np.arange(len(values))
        bars = ax.bar(positions, values)
        ax.set_ylim(0, 40)

        mixin._add_bar_value_labels(
            ax=ax,
            bars=bars,
            values=values,
            orientation="vertical",
            value_format="integer",
            value_suffix=" kg",
            value_offset=1,
            fontsize=10,
            color="black",
            weight="normal",
            baseline=0,
        )

        texts = ax.texts
        assert len(texts) == 3

        for text in texts:
            assert text.get_text().endswith(" kg"), f"'{text.get_text()}' missing suffix"


class TestMixinIntegration:
    """Tests for mixin working with real chart views."""

    def test_bar_chart_view_inherits_mixin_methods(self):
        """BarChartView has all mixin methods accessible."""
        from tpsplots.views import BarChartView

        view = BarChartView()

        # Verify all mixin methods are available
        assert hasattr(view, "_determine_bar_colors")
        assert hasattr(view, "_add_bar_value_labels")
        assert hasattr(view, "_add_value_based_legend")
        assert hasattr(view, "_apply_percentage_tick_formatter")
        assert hasattr(view, "_apply_common_bar_styling")

        # Verify required dependencies from ChartView are present
        assert hasattr(view, "TPS_COLORS")
        assert hasattr(view, "_format_value")

    def test_grouped_bar_chart_uses_mixin_colors(self):
        """GroupedBarChartView color assignment uses mixin logic."""
        from tpsplots.views.grouped_bar_chart import GroupedBarChartView

        view = GroupedBarChartView()

        # Test positive/negative color assignment
        colors = view._determine_bar_colors([1, -1], None, "#pos", "#neg")
        assert colors == ["#pos", "#neg"]

        # Test color cycling
        colors = view._determine_bar_colors([1, 2, 3], ["#A", "#B"], None, None)
        assert colors == ["#A", "#B", "#A"]
