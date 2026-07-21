"""Chart views for the TPS Plots package."""

from .area_chart import AreaChartView
from .bar_chart import BarChartView
from .chart_view import ChartView
from .donut_chart import DonutChartView
from .grouped_bar_chart import GroupedBarChartView
from .line_chart import LineChartView
from .line_subplots import LineSubplotsView
from .lollipop_chart import LollipopChartView
from .mixins import BarChartMixin
from .scatter_chart import ScatterChartView
from .stacked_bar_chart import StackedBarChartView
from .treemap_chart import TreemapChartView
from .us_map_pie_charts import USMapPieChartView
from .waffle_chart import WaffleChartView

# Centralized registry mapping chart type names to view classes
# This is the single source of truth for available chart types
VIEW_REGISTRY: dict[str, type[ChartView]] = {
    "area_plot": AreaChartView,
    "line_plot": LineChartView,
    "scatter_plot": ScatterChartView,
    "bar_plot": BarChartView,
    "donut_plot": DonutChartView,
    "lollipop_plot": LollipopChartView,
    "stacked_bar_plot": StackedBarChartView,
    "treemap_plot": TreemapChartView,
    "waffle_plot": WaffleChartView,
    "us_map_pie_plot": USMapPieChartView,
    "line_subplots_plot": LineSubplotsView,
    "grouped_bar_plot": GroupedBarChartView,
}

# Export these classes as the public API
__all__ = [
    "VIEW_REGISTRY",
    "AreaChartView",
    "BarChartMixin",
    "BarChartView",
    "ChartView",
    "DonutChartView",
    "GroupedBarChartView",
    "LineChartView",
    "LineSubplotsView",
    "LollipopChartView",
    "ScatterChartView",
    "StackedBarChartView",
    "TreemapChartView",
    "USMapPieChartView",
    "WaffleChartView",
]
