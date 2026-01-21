"""Shared pytest fixtures for tpsplots tests."""

import matplotlib.pyplot as plt
import pytest


@pytest.fixture
def mixin():
    """
    Provide a BarChartView instance with all BarChartMixin dependencies.

    BarChartView inherits from BarChartMixin and ChartView, giving it access to:
    - TPS_COLORS dict (from ChartView)
    - _format_value method (from ChartView)
    - All mixin methods we want to test
    """
    from tpsplots.views import BarChartView

    return BarChartView()


@pytest.fixture
def mixin_with_color_cycle():
    """
    Provide a view instance with ColorCycleMixin dependencies.

    StackedBarChartView inherits from ColorCycleMixin and ChartView, giving it access to:
    - TPS_COLORS dict (from ChartView)
    - _get_cycled_colors method (from ColorCycleMixin)
    """
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    return StackedBarChartView()


@pytest.fixture
def ax():
    """
    Provide fresh matplotlib axes for each test.

    Yields the axes and properly closes the figure after test completion
    to prevent memory leaks during test runs.
    """
    fig, ax = plt.subplots()
    yield ax
    plt.close(fig)


# Reusable test data constants
SAMPLE_VALUES = [10, 20, -5, 30, -15]
SAMPLE_POSITIVE = [10, 20, 30]
SAMPLE_NEGATIVE = [-10, -20, -30]
SAMPLE_COLORS = ["#FF0000", "#00FF00", "#0000FF"]
