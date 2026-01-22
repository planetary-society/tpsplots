"""YAML-driven chart generation processor (v2.0 spec)."""

import logging
from pathlib import Path
from typing import Any, ClassVar

import yaml

from tpsplots.exceptions import ConfigurationError
from tpsplots.models import YAMLChartConfig
from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.processors.resolvers import (
    ColorResolver,
    DataResolver,
    MetadataResolver,
    ParameterResolver,
)
from tpsplots.views import VIEW_REGISTRY

logger = logging.getLogger(__name__)


class YAMLChartProcessor:
    """Processes YAML configuration files to generate charts (v2.0 spec)."""

    # Use the centralized registry from views module
    VIEW_REGISTRY: ClassVar[dict[str, type]] = VIEW_REGISTRY

    def __init__(self, yaml_path: str | Path, outdir: Path | None = None, *, strict: bool = False):
        """
        Initialize the YAML chart processor.

        Args:
            yaml_path: Path to YAML configuration file
            outdir: Output directory for charts (default: charts/)
            strict: If True, fail on unresolved references (default: True in v2.0)
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
        """Get the appropriate view instance for the chart type.

        Args:
            chart_type: The v1.0 chart type name (e.g., 'line_plot')
        """
        view_class = self.VIEW_REGISTRY.get(chart_type)
        if view_class is None:
            available = list(self.VIEW_REGISTRY.keys())
            raise ConfigurationError(
                f"Unknown chart type: {chart_type}. Available types: {available}"
            )
        return view_class(outdir=self.outdir)

    def generate_chart(self) -> dict[str, Any]:
        """Generate the chart based on the YAML configuration."""
        # Step 1: Resolve data source
        logger.info("Resolving data source...")
        self.data = DataResolver.resolve(self.config.data)

        # Step 2: Extract chart configuration
        chart = self.config.chart

        # Get all chart parameters (everything in chart except type, output, title, subtitle, source)
        chart_dict = chart.model_dump(exclude_none=True)

        # Extract metadata fields
        metadata_fields = {"title", "subtitle", "source"}
        metadata = {k: chart_dict.pop(k) for k in metadata_fields if k in chart_dict}

        # Extract control fields
        chart_type_v2 = chart_dict.pop("type")
        output_name = chart_dict.pop("output")

        # Map v2.0 type to v1.0 method name
        chart_type_v1 = CHART_TYPES.get(chart_type_v2, f"{chart_type_v2}_plot")

        # Remaining fields are chart parameters
        parameters = chart_dict

        # Step 3: Resolve {{...}} references in parameters and metadata
        logger.info("Resolving references...")
        resolved_params = ParameterResolver.resolve(parameters, self.data)
        resolved_metadata = MetadataResolver.resolve(metadata, self.data)

        # Step 3b: Resolve semantic color names to hex codes
        color_params = [
            "color",
            "colors",
            "positive_color",
            "negative_color",
            "value_color",
            "center_color",
            "start_marker_color",
            "end_marker_color",
            "start_marker_edgecolor",
            "end_marker_edgecolor",
            "y_tick_color",
            "line_colors",
            "hline_colors",
            "edgecolor",
            "pie_edge_color",
            "offset_line_color",
        ]
        for param in color_params:
            if param in resolved_params:
                resolved_params[param] = ColorResolver.resolve(resolved_params[param])

        # Step 4: Get view and generate chart
        logger.info(f"Generating {chart_type_v2} chart: {output_name}")
        self.view = self._get_view(chart_type_v1)

        # Call the appropriate plot method
        plot_method = getattr(self.view, chart_type_v1)
        result = plot_method(metadata=resolved_metadata, stem=output_name, **resolved_params)

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
