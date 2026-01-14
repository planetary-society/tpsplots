"""Chart views for the TPS Plots package."""

from .bar_chart import BarChartView
from .chart_view import ChartView
from .donut_chart import DonutChartView
from .line_chart import LineChartView
from .line_subplots import LineSubplotsView
from .lollipop_chart import LollipopChartView
from .stacked_bar_chart import StackedBarChartView
from .us_map_pie_charts import USMapPieChartView
from .waffle_chart import WaffleChartView

# Centralized registry mapping chart type names to view classes
# This is the single source of truth for available chart types
VIEW_REGISTRY: dict[str, type[ChartView]] = {
    "line_plot": LineChartView,
    "bar_plot": BarChartView,
    "donut_plot": DonutChartView,
    "lollipop_plot": LollipopChartView,
    "stacked_bar_plot": StackedBarChartView,
    "waffle_plot": WaffleChartView,
    "us_map_pie_plot": USMapPieChartView,
    "line_subplots_plot": LineSubplotsView,
}

# Export these classes as the public API
__all__ = [
    # View classes
    "BarChartView",
    "ChartView",
    "DonutChartView",
    "LineChartView",
    "LineSubplotsView",
    "LollipopChartView",
    "StackedBarChartView",
    "USMapPieChartView",
    "WaffleChartView",
    # Registry
    "VIEW_REGISTRY",
]
