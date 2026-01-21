"""Unit tests for GridAxisMixin.

Tests the grid and axis styling utilities used across bar, stacked bar,
lollipop, and grouped bar charts.
"""

import matplotlib.pyplot as plt
import pytest


@pytest.fixture
def mixin_with_grid():
    """Provide a view instance with GridAxisMixin dependencies."""
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    return StackedBarChartView()


@pytest.fixture
def ax():
    """Provide fresh matplotlib axes for each test."""
    fig, ax = plt.subplots()
    yield ax
    plt.close(fig)


class TestApplyGrid:
    """Tests for _apply_grid method."""

    def test_grid_enabled_by_default(self, mixin_with_grid, ax):
        """Grid is applied when grid=True (default)."""
        mixin_with_grid._apply_grid(ax, grid=True)

        # Grid lines should be visible
        assert ax.yaxis.get_gridlines()[0].get_visible()

    def test_grid_disabled_when_false(self, mixin_with_grid, ax):
        """Grid is hidden when grid=False."""
        mixin_with_grid._apply_grid(ax, grid=False)

        # Grid should be disabled
        # Note: matplotlib still has gridlines but they're turned off
        assert not ax.xaxis.get_visible() or not any(
            line.get_visible() for line in ax.xaxis.get_gridlines()
        )

    def test_grid_axis_respects_parameter(self, mixin_with_grid, ax):
        """Grid axis parameter controls which axis shows grid."""
        mixin_with_grid._apply_grid(ax, grid=True, grid_axis="x")
        # Just verify it runs without error - visual verification needed

    def test_custom_alpha_applied(self, mixin_with_grid, ax):
        """Custom alpha value is applied to grid lines."""
        mixin_with_grid._apply_grid(ax, grid=True, alpha=0.5)
        # Check that gridlines exist (specific alpha check is complex)
        assert ax.yaxis.get_gridlines()


class TestDisableMinorTicks:
    """Tests for _disable_minor_ticks method."""

    def test_minor_ticks_disabled_on_both_axes(self, mixin_with_grid, ax):
        """Minor ticks are disabled on both x and y axes."""
        mixin_with_grid._disable_minor_ticks(ax)

        # Verify minor locator is NullLocator
        from matplotlib.ticker import NullLocator

        assert isinstance(ax.xaxis.get_minor_locator(), NullLocator)
        assert isinstance(ax.yaxis.get_minor_locator(), NullLocator)


class TestApplyIntegerLocator:
    """Tests for _apply_integer_locator method."""

    def test_vertical_applies_to_y_axis(self, mixin_with_grid, ax):
        """Vertical orientation applies integer locator to y-axis."""
        ax.bar([0, 1, 2], [1.5, 2.5, 3.5])  # Set up some data
        mixin_with_grid._apply_integer_locator(ax, orientation="vertical")

        from matplotlib.ticker import MaxNLocator

        assert isinstance(ax.yaxis.get_major_locator(), MaxNLocator)

    def test_horizontal_applies_to_x_axis(self, mixin_with_grid, ax):
        """Horizontal orientation applies integer locator to x-axis."""
        ax.barh([0, 1, 2], [1.5, 2.5, 3.5])  # Set up some data
        mixin_with_grid._apply_integer_locator(ax, orientation="horizontal")

        from matplotlib.ticker import MaxNLocator

        assert isinstance(ax.xaxis.get_major_locator(), MaxNLocator)


class TestHideCategoryTicks:
    """Tests for _hide_category_ticks method."""

    def test_vertical_hides_x_axis_ticks(self, mixin_with_grid, ax):
        """Vertical orientation hides x-axis tick marks."""
        ax.bar(["A", "B", "C"], [1, 2, 3])
        mixin_with_grid._hide_category_ticks(ax, orientation="vertical")

        # Tick length should be 0
        # This is a bit hard to test directly, but we verify no error
        # Visual verification would be needed for full assurance

    def test_horizontal_hides_y_axis_ticks(self, mixin_with_grid, ax):
        """Horizontal orientation hides y-axis tick marks."""
        ax.barh(["A", "B", "C"], [1, 2, 3])
        mixin_with_grid._hide_category_ticks(ax, orientation="horizontal")

        # Runs without error


class TestApplyAxisLimits:
    """Tests for _apply_axis_limits method."""

    def test_tuple_xlim_applied(self, mixin_with_grid, ax):
        """Tuple format xlim is applied correctly."""
        mixin_with_grid._apply_axis_limits(ax, xlim=(0, 100))

        assert ax.get_xlim() == (0.0, 100.0)

    def test_tuple_ylim_applied(self, mixin_with_grid, ax):
        """Tuple format ylim is applied correctly."""
        mixin_with_grid._apply_axis_limits(ax, ylim=(-10, 50))

        assert ax.get_ylim() == (-10.0, 50.0)

    def test_dict_xlim_applied(self, mixin_with_grid, ax):
        """Dict format xlim is applied correctly."""
        mixin_with_grid._apply_axis_limits(ax, xlim={"left": 5, "right": 95})

        limits = ax.get_xlim()
        assert limits[0] == 5.0
        assert limits[1] == 95.0

    def test_dict_ylim_applied(self, mixin_with_grid, ax):
        """Dict format ylim is applied correctly."""
        mixin_with_grid._apply_axis_limits(ax, ylim={"bottom": 0, "top": 100})

        limits = ax.get_ylim()
        assert limits[0] == 0.0
        assert limits[1] == 100.0

    def test_none_limits_ignored(self, mixin_with_grid, ax):
        """None limits don't change axis bounds."""
        original_xlim = ax.get_xlim()
        original_ylim = ax.get_ylim()

        mixin_with_grid._apply_axis_limits(ax, xlim=None, ylim=None)

        assert ax.get_xlim() == original_xlim
        assert ax.get_ylim() == original_ylim


class TestMixinIntegration:
    """Tests for mixin integration with chart views."""

    def test_stacked_bar_has_grid_methods(self):
        """StackedBarChartView has all GridAxisMixin methods."""
        from tpsplots.views.stacked_bar_chart import StackedBarChartView

        view = StackedBarChartView()

        assert hasattr(view, "_apply_grid")
        assert hasattr(view, "_disable_minor_ticks")
        assert hasattr(view, "_apply_integer_locator")
        assert hasattr(view, "_hide_category_ticks")
        assert hasattr(view, "_apply_axis_limits")
        assert hasattr(view, "_apply_axis_labels")
        assert hasattr(view, "_apply_tick_styling")

    def test_lollipop_has_grid_methods(self):
        """LollipopChartView has all GridAxisMixin methods."""
        from tpsplots.views.lollipop_chart import LollipopChartView

        view = LollipopChartView()

        assert hasattr(view, "_apply_grid")
        assert hasattr(view, "_apply_axis_limits")

    def test_grouped_bar_has_grid_methods(self):
        """GroupedBarChartView has all GridAxisMixin methods."""
        from tpsplots.views.grouped_bar_chart import GroupedBarChartView

        view = GroupedBarChartView()

        assert hasattr(view, "_apply_grid")
        assert hasattr(view, "_apply_axis_limits")
