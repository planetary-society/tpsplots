"""Scatter chart configuration model.

ScatterChartView is a thin subclass of LineChartView that sets marker='o'
and linestyle='None' by default. The config mirrors this inheritance.
"""

from typing import Literal

from pydantic import Field

from tpsplots.models.charts.line import LineChartConfig


class ScatterChartConfig(LineChartConfig):
    """Validated configuration for ``type: scatter`` charts.

    Inherits all fields from LineChartConfig. The scatter view delegates
    entirely to the line chart rendering pipeline with different defaults.
    """

    type: Literal["scatter"] = Field("scatter", description="Chart type discriminator")
