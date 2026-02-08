"""YAML-driven chart generation processor (v2.0 spec)."""

import logging
from pathlib import Path
from typing import Any, ClassVar

import yaml

from tpsplots.exceptions import ConfigurationError
from tpsplots.models import YAMLChartConfig
from tpsplots.processors.render_pipeline import build_render_context
from tpsplots.processors.resolvers import DataResolver
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

        # Step 2: Build render context (shared with editor preview)
        ctx = build_render_context(self.config, self.data, log_conflicts=True)

        # Step 3: Get view and generate chart
        logger.info(f"Generating chart: {ctx.output_name}")
        self.view = self._get_view(ctx.chart_type_v1)

        plot_method = getattr(self.view, ctx.chart_type_v1)
        result = plot_method(
            metadata=ctx.resolved_metadata,
            stem=ctx.output_name,
            **ctx.resolved_params,
        )

        logger.info(f"Successfully generated chart: {ctx.output_name}")
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
