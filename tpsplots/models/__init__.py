"""Pydantic models for YAML chart configuration (v2.0 spec)."""

from tpsplots.models.chart_config import (
    CHART_TYPES,
    ChartConfig,
    ChartType,
    MetadataConfig,
)
from tpsplots.models.charts import (
    CONFIG_REGISTRY,
    BarChartConfig,
    DirectLineLabelsConfig,
    DonutChartConfig,
    GroupConfig,
    GroupedBarChartConfig,
    LineChartConfig,
    LineSubplotsChartConfig,
    LollipopChartConfig,
    ScatterChartConfig,
    SeriesConfig,
    StackedBarChartConfig,
    USMapPieChartConfig,
    WaffleChartConfig,
)
from tpsplots.models.data_sources import DataSource, DataSourceConfig
from tpsplots.models.parameters import ParametersConfig
from tpsplots.models.yaml_config import YAMLChartConfig

__all__ = [
    # Registries
    "CHART_TYPES",
    "CONFIG_REGISTRY",
    # Per-chart config models
    "BarChartConfig",
    "ChartConfig",
    "ChartType",
    # Data sources
    "DataSource",
    "DataSourceConfig",
    # Sub-models
    "DirectLineLabelsConfig",
    "DonutChartConfig",
    "GroupConfig",
    "GroupedBarChartConfig",
    "LineChartConfig",
    "LineSubplotsChartConfig",
    "LollipopChartConfig",
    "MetadataConfig",
    # Parameters (deprecated — use per-chart config models instead)
    "ParametersConfig",
    "ScatterChartConfig",
    "SeriesConfig",
    "StackedBarChartConfig",
    "USMapPieChartConfig",
    "WaffleChartConfig",
    # Top-level config
    "YAMLChartConfig",
]
