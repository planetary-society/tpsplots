"""Complete YAML chart configuration schema (v2.0 spec)."""

from pydantic import BaseModel, Field

from tpsplots.models.chart_config import ChartConfig
from tpsplots.models.data_sources import DataSourceConfig


class YAMLChartConfig(BaseModel):
    """Complete YAML chart configuration schema (v2.0).

    The v2.0 spec uses a two-level structure:
    - `data:` - where the data comes from
    - `chart:` - how to display it (includes type, output, metadata, and parameters)

    Example:
        data:
          source: data/budget.csv

        chart:
          type: line
          output: budget_chart
          title: "NASA Budget Over Time"
          subtitle: "Inflation-adjusted dollars"
          source: "NASA Budget Office"

          x: "{{Year}}"
          y: "{{Budget}}"
          color: NeptuneBlue
          scale: billions
    """

    data: DataSourceConfig = Field(..., description="Data source configuration")
    chart: ChartConfig = Field(
        ..., description="Chart configuration including type, metadata, and parameters"
    )
