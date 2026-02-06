"""Per-chart-type Pydantic config models.

Each chart type has a dedicated config model that validates all accepted
parameters at YAML load time. The ``CONFIG_REGISTRY`` maps chart type
strings to their config classes for O(1) dispatch.
"""

from tpsplots.models.charts.bar import BarChartConfig
from tpsplots.models.charts.donut import DonutChartConfig
from tpsplots.models.charts.grouped_bar import GroupConfig, GroupedBarChartConfig
from tpsplots.models.charts.line import (
    DirectLineLabelsConfig,
    LineChartConfig,
    SeriesConfig,
)
from tpsplots.models.charts.line_subplots import LineSubplotsChartConfig
from tpsplots.models.charts.lollipop import LollipopChartConfig
from tpsplots.models.charts.scatter import ScatterChartConfig
from tpsplots.models.charts.stacked_bar import StackedBarChartConfig
from tpsplots.models.charts.us_map_pie import USMapPieChartConfig
from tpsplots.models.charts.waffle import WaffleChartConfig

# Registry: chart type string → config class
CONFIG_REGISTRY: dict[str, type] = {
    "line": LineChartConfig,
    "scatter": ScatterChartConfig,
    "bar": BarChartConfig,
    "donut": DonutChartConfig,
    "lollipop": LollipopChartConfig,
    "stacked_bar": StackedBarChartConfig,
    "waffle": WaffleChartConfig,
    "grouped_bar": GroupedBarChartConfig,
    "us_map_pie": USMapPieChartConfig,
    "line_subplots": LineSubplotsChartConfig,
}

__all__ = [
    # Registry
    "CONFIG_REGISTRY",
    # Config models
    "BarChartConfig",
    # Sub-models
    "DirectLineLabelsConfig",
    "DonutChartConfig",
    "GroupConfig",
    "GroupedBarChartConfig",
    "LineChartConfig",
    "LineSubplotsChartConfig",
    "LollipopChartConfig",
    "ScatterChartConfig",
    "SeriesConfig",
    "StackedBarChartConfig",
    "USMapPieChartConfig",
    "WaffleChartConfig",
]
