"""YAML-driven chart generation processor."""

import logging
from pathlib import Path
from typing import Any, ClassVar

import yaml

from tpsplots.exceptions import ConfigurationError
from tpsplots.models import YAMLChartConfig
from tpsplots.processors.resolvers import DataResolver, MetadataResolver, ParameterResolver
from tpsplots.views import VIEW_REGISTRY

logger = logging.getLogger(__name__)


class YAMLChartProcessor:
    """Processes YAML configuration files to generate charts."""

    # Use the centralized registry from views module
    VIEW_REGISTRY: ClassVar[dict[str, type]] = VIEW_REGISTRY

    def __init__(
        self, yaml_path: str | Path, outdir: Path | None = None, *, strict: bool = False
    ):
        """
        Initialize the YAML chart processor.

        Args:
            yaml_path: Path to YAML configuration file
            outdir: Output directory for charts (default: charts/)
        """
        self.yaml_path = Path(yaml_path)
        self.outdir = outdir or Path("charts")
        self.strict = strict

        # Load and validate YAML configuration
        raw_config = self._load_yaml()
        self.config = self._validate_config(raw_config)

        self.data: dict[str, Any] | None = None
        self.view = None

    def _load_yaml(self) -> dict[str, Any]:
        """Load and parse YAML configuration file."""
        try:
            with open(self.yaml_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded YAML config from {self.yaml_path}")
            return config
        except FileNotFoundError as e:
            raise ConfigurationError(f"YAML file not found: {self.yaml_path}") from e
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax in {self.yaml_path}: {e}") from e

    def _validate_config(self, raw_config: dict[str, Any]) -> YAMLChartConfig:
        """Validate the YAML configuration using Pydantic."""
        try:
            config = YAMLChartConfig(**raw_config)
            logger.info("YAML configuration validated successfully")
            return config
        except Exception as e:
            raise ConfigurationError(f"YAML configuration validation failed: {e}") from e

    def _get_view(self, chart_type: str):
        """Get the appropriate view instance for the chart type."""
        view_class = self.VIEW_REGISTRY[chart_type]
        return view_class(outdir=self.outdir)

    def generate_chart(self) -> dict[str, Any]:
        """Generate the chart based on the YAML configuration."""
        # Step 1: Resolve data source
        logger.info("Resolving data source...")
        self.data = DataResolver.resolve(self.config.data_source)

        # Step 2: Resolve parameters with data context
        logger.info("Resolving parameters...")
        parameters = ParameterResolver.resolve(self.config.parameters, self.data, strict=self.strict)

        # Step 3: Resolve metadata templates
        logger.info("Resolving metadata...")
        metadata = MetadataResolver.resolve(self.config.metadata, self.data, strict=self.strict)

        # Step 4: Get view and generate chart
        chart_config = self.config.chart
        chart_type = chart_config.type
        output_name = chart_config.output_name

        logger.info(f"Generating {chart_type} chart: {output_name}")
        self.view = self._get_view(chart_type)

        # Call the appropriate plot method
        plot_method = getattr(self.view, chart_type)
        result = plot_method(metadata=metadata, stem=output_name, **parameters)

        logger.info(f"Successfully generated chart: {output_name}")
        return result


def create_yaml_directories():
    """Create necessary directories for YAML chart system."""
    yaml_dir = Path("yaml")
    yaml_dir.mkdir(exist_ok=True)

    charts_dir = Path("charts")
    charts_dir.mkdir(exist_ok=True)


if __name__ == "__main__":
    # Simple command-line test
    import sys

    if len(sys.argv) > 1:
        yaml_path = sys.argv[1]
        processor = YAMLChartProcessor(yaml_path)
        processor.generate_chart()
    else:
        print("Usage: python yaml_chart_processor.py <yaml_file>")
