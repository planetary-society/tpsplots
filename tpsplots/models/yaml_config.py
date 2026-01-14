"""Complete YAML chart configuration schema."""

from pydantic import BaseModel, Field, model_validator

from tpsplots.models.chart_config import ChartConfig, MetadataConfig
from tpsplots.models.data_sources import (
    ControllerMethodDataSource,
    CSVFileDataSource,
    GoogleSheetsDataSource,
)
from tpsplots.models.parameters import ParametersConfig


class YAMLChartConfig(BaseModel):
    """Complete YAML chart configuration schema."""

    chart: ChartConfig
    data_source: ControllerMethodDataSource | CSVFileDataSource | GoogleSheetsDataSource = Field(
        ..., discriminator="type"
    )
    metadata: MetadataConfig
    parameters: ParametersConfig

    @model_validator(mode="after")
    def validate_data_source_fields(self) -> "YAMLChartConfig":
        """Validate data source has required fields based on type."""
        data_source = self.data_source
        if not data_source:
            return self

        if data_source.type == "controller_method":
            if not hasattr(data_source, "class_name") or not hasattr(data_source, "method"):
                raise ValueError("controller_method requires 'class' and 'method' fields")
        elif data_source.type == "csv_file":
            if not hasattr(data_source, "path"):
                raise ValueError("csv_file requires 'path' field")
        elif data_source.type == "google_sheets" and not hasattr(data_source, "url"):
            raise ValueError("google_sheets requires 'url' field")

        return self
