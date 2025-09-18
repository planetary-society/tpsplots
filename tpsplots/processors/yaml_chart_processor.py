"""YAML-driven chart generation processor with Pydantic validation."""
import yaml
import pandas as pd
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Literal
import logging
import re

from pydantic import BaseModel, Field, validator, model_validator

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.views import (
    LineChartView, BarChartView, DonutChartView, LollipopChartView,
    StackedBarChartView, WaffleChartView, USMapPieChartView, LineSubplotsView
)

logger = logging.getLogger(__name__)


# Pydantic models for YAML validation
class ChartConfig(BaseModel):
    """Chart configuration section."""
    type: Literal[
        'line_plot', 'bar_plot', 'donut_plot', 'lollipop_plot',
        'stacked_bar_plot', 'waffle_plot', 'us_map_pie_plot', 'line_subplots_plot'
    ] = Field(..., description="Chart type matching view method names")
    output_name: str = Field(..., description="Base filename for chart outputs")


class ControllerMethodDataSource(BaseModel):
    """Controller method data source configuration."""
    type: Literal['controller_method']
    class_name: str = Field(..., alias='class', description="Controller class name")
    method: str = Field(..., description="Method name to call")


class CSVFileDataSource(BaseModel):
    """CSV file data source configuration."""
    type: Literal['csv_file']
    path: str = Field(..., description="Path to CSV file")


class URLDataSource(BaseModel):
    """URL/Google Sheets data source configuration."""
    type: Literal['google_sheets', 'url']
    url: str = Field(..., description="URL to fetch CSV data from")


class MetadataConfig(BaseModel):
    """Chart metadata configuration."""
    title: str = Field(..., description="Chart title")
    subtitle: Optional[str] = Field(None, description="Chart subtitle (supports templates)")
    source: Optional[str] = Field(None, description="Data source attribution")
    header: Optional[bool] = Field(None, description="Show header section")
    footer: Optional[bool] = Field(None, description="Show footer section")


class DirectLineLabelsConfig(BaseModel):
    """Configuration for direct line labels."""
    fontsize: Optional[int] = Field(None, description="Font size for labels")
    position: Optional[Literal['right', 'left', 'auto']] = Field('auto', description="Label position")
    bbox: Optional[bool] = Field(True, description="Add background box to labels")


class ParametersConfig(BaseModel):
    """Chart parameters configuration."""
    # Data mapping - most can be strings (data references) or actual values
    x: Optional[str] = Field(None, description="X-axis data reference")
    y: Optional[Union[str, List[str]]] = Field(None, description="Y-axis data reference(s)")
    color: Optional[Union[str, List[str]]] = Field(None, description="Color specification")
    linestyle: Optional[Union[str, List[str]]] = Field(None, description="Line style specification")
    linewidth: Optional[Union[float, List[float], str, List[str]]] = Field(None, description="Line width specification")
    marker: Optional[Union[str, List[str]]] = Field(None, description="Marker specification")
    label: Optional[Union[str, List[str]]] = Field(None, description="Label specification")

    # Axis configuration
    xlim: Optional[Union[List[float], str]] = Field(None, description="X-axis limits [min, max] or data reference")
    ylim: Optional[Union[List[float], str]] = Field(None, description="Y-axis limits [min, max] or data reference")
    xlabel: Optional[str] = Field(None, description="X-axis label")
    ylabel: Optional[str] = Field(None, description="Y-axis label")

    # Styling
    label_size: Optional[Union[int, str]] = Field(None, description="Label font size or data reference")
    tick_size: Optional[Union[int, str]] = Field(None, description="Tick font size or data reference")
    grid: Optional[Union[bool, str]] = Field(None, description="Show grid or data reference")
    legend: Optional[Union[bool, str]] = Field(None, description="Show legend or data reference")

    # Advanced features
    direct_line_labels: Optional[Union[DirectLineLabelsConfig, str]] = Field(None, description="Direct line labels config")

    # Export
    export_data: Optional[str] = Field(None, description="Export data reference")

    class Config:
        extra = "allow"  # Allow additional parameters not explicitly defined

    @validator('ylim', 'xlim')
    def validate_limits(cls, v):
        """Validate that limits are [min, max] format when they're lists."""
        if v is not None and isinstance(v, list) and len(v) != 2:
            raise ValueError("Limits must be [min, max] format")
        return v


class YAMLChartConfig(BaseModel):
    """Complete YAML chart configuration schema."""
    chart: ChartConfig
    data_source: Union[ControllerMethodDataSource, CSVFileDataSource, URLDataSource] = Field(
        ..., discriminator='type'
    )
    metadata: MetadataConfig
    parameters: ParametersConfig

    @model_validator(mode='after')
    def validate_data_source_fields(self):
        """Validate data source has required fields based on type."""
        data_source = self.data_source
        if not data_source:
            return self

        if data_source.type == 'controller_method':
            if not hasattr(data_source, 'class_name') or not hasattr(data_source, 'method'):
                raise ValueError("controller_method requires 'class' and 'method' fields")
        elif data_source.type == 'csv_file':
            if not hasattr(data_source, 'path'):
                raise ValueError("csv_file requires 'path' field")
        elif data_source.type in ['google_sheets', 'url']:
            if not hasattr(data_source, 'url'):
                raise ValueError(f"{data_source.type} requires 'url' field")

        return self


class YAMLChartProcessor:
    """Processes YAML configuration files to generate charts with Pydantic validation."""

    # Map chart types to view classes
    VIEW_REGISTRY = {
        'line_plot': LineChartView,
        'bar_plot': BarChartView,
        'donut_plot': DonutChartView,
        'lollipop_plot': LollipopChartView,
        'stacked_bar_plot': StackedBarChartView,
        'waffle_plot': WaffleChartView,
        'us_map_pie_plot': USMapPieChartView,
        'line_subplots_plot': LineSubplotsView,
    }

    def __init__(self, yaml_path: Union[str, Path], outdir: Optional[Path] = None):
        """
        Initialize the YAML chart processor.

        Args:
            yaml_path: Path to YAML configuration file
            outdir: Output directory for charts (default: charts/)
        """
        self.yaml_path = Path(yaml_path)
        self.outdir = outdir or Path("charts")

        # Load and validate YAML configuration
        raw_config = self._load_yaml()
        self.config = self._validate_config(raw_config)

        self.data = None
        self.view = None

    def _load_yaml(self) -> Dict[str, Any]:
        """Load and parse YAML configuration file."""
        try:
            with open(self.yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded YAML config from {self.yaml_path}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(f"YAML file not found: {self.yaml_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.yaml_path}: {e}")

    def _validate_config(self, raw_config: Dict[str, Any]) -> YAMLChartConfig:
        """Validate the YAML configuration using Pydantic."""
        try:
            config = YAMLChartConfig(**raw_config)
            logger.info("YAML configuration validated successfully")
            return config
        except Exception as e:
            raise ValueError(f"YAML configuration validation failed: {e}")

    def _resolve_data_source(self) -> Dict[str, Any]:
        """Resolve the data source and return the processed data."""
        data_source = self.config.data_source

        if data_source.type == 'controller_method':
            return self._resolve_controller_method(data_source)
        elif data_source.type == 'csv_file':
            return self._resolve_csv_file(data_source)
        elif data_source.type in ['google_sheets', 'url']:
            return self._resolve_google_sheets_data(data_source)
        else:
            raise ValueError(f"Unsupported data source type: {data_source.type}")

    def _resolve_controller_method(self, data_source: ControllerMethodDataSource) -> Dict[str, Any]:
        """Resolve data from a controller method."""
        class_name = data_source.class_name
        method_name = data_source.method

        try:
            # Dynamic import of controller class
            # First try from tpsplots.controllers
            try:
                module_path = f"tpsplots.controllers.{self._snake_case(class_name)}"
                module = importlib.import_module(module_path)
                controller_class = getattr(module, class_name)
            except (ImportError, AttributeError):
                # Fallback: try to find the class in any controllers module
                controller_class = self._find_controller_class(class_name)

            # Instantiate controller
            controller = controller_class()

            # Get the method
            if not hasattr(controller, method_name):
                raise AttributeError(f"Controller {class_name} has no method '{method_name}'")

            method = getattr(controller, method_name)

            # Call the method and return result
            result = method()
            logger.info(f"Retrieved data from {class_name}.{method_name}")

            # If method returns a dict, use it directly
            # If it returns something else, wrap it
            if isinstance(result, dict):
                return result
            else:
                return {'data': result}

        except Exception as e:
            raise RuntimeError(f"Error calling {class_name}.{method_name}: {e}")

    def _find_controller_class(self, class_name: str):
        """Find controller class by searching all controller modules."""
        controllers_dir = Path(__file__).parent.parent / "controllers"

        for py_file in controllers_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            module_name = py_file.stem
            try:
                module = importlib.import_module(f"tpsplots.controllers.{module_name}")
                if hasattr(module, class_name):
                    return getattr(module, class_name)
            except ImportError:
                continue

        raise ImportError(f"Could not find controller class '{class_name}'")

    def _snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _resolve_csv_file(self, data_source: CSVFileDataSource) -> Dict[str, Any]:
        """Resolve data from a CSV file using CSVController."""
        try:
            from tpsplots.controllers.csv_controller import CSVController
            controller = CSVController(csv_path=data_source.path)
            return controller.load_data()
        except Exception as e:
            raise RuntimeError(f"Error loading CSV data via CSVController: {e}")

    def _resolve_google_sheets_data(self, data_source: URLDataSource) -> Dict[str, Any]:
        """Resolve data from Google Sheets or URL using GoogleSheetsController."""
        try:
            from tpsplots.controllers.google_sheets_controller import GoogleSheetsController
            controller = GoogleSheetsController(url=data_source.url)
            return controller.load_data()
        except Exception as e:
            raise RuntimeError(f"Error loading Google Sheets data via GoogleSheetsController: {e}")

    def _resolve_parameters(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameters by substituting data references."""
        # Convert Pydantic model to dict, excluding None values
        parameters = self.config.parameters.dict(exclude_none=True)
        resolved = {}

        for key, value in parameters.items():
            resolved[key] = self._resolve_value(value, data)

        return resolved

    def _resolve_value(self, value: Any, data: Dict[str, Any]) -> Any:
        """Recursively resolve a parameter value against the data context."""
        if isinstance(value, str):
            # Check if it's a data reference (simple key lookup)
            if value in data:
                return data[value]
            else:
                return value
        elif isinstance(value, list):
            return [self._resolve_value(item, data) for item in value]
        elif isinstance(value, dict):
            return {k: self._resolve_value(v, data) for k, v in value.items()}
        else:
            return value

    def _resolve_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve metadata by substituting template variables."""
        # Convert Pydantic model to dict, excluding None values
        metadata = self.config.metadata.dict(exclude_none=True)

        for key, value in metadata.items():
            if isinstance(value, str):
                # Template substitution using data context
                try:
                    # Support both {data.key} and {key} syntax
                    # Create a safe format context without key conflicts
                    format_context = data.copy()
                    format_context['data'] = data
                    metadata[key] = value.format(**format_context)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Could not resolve template in metadata.{key}: {e}")
                    # Keep original value if template resolution fails

        return metadata

    def _get_view(self, chart_type: str):
        """Get the appropriate view instance for the chart type."""
        view_class = self.VIEW_REGISTRY[chart_type]
        return view_class(outdir=self.outdir)

    def generate_chart(self) -> Dict[str, Any]:
        """Generate the chart based on the YAML configuration."""
        try:
            # Step 1: Resolve data source
            logger.info("Resolving data source...")
            self.data = self._resolve_data_source()

            # Step 2: Resolve parameters with data context
            logger.info("Resolving parameters...")
            parameters = self._resolve_parameters(self.data)

            # Step 3: Resolve metadata templates
            logger.info("Resolving metadata...")
            metadata = self._resolve_metadata(self.data)

            # Step 4: Get view and generate chart
            chart_config = self.config.chart
            chart_type = chart_config.type
            output_name = chart_config.output_name

            logger.info(f"Generating {chart_type} chart: {output_name}")
            self.view = self._get_view(chart_type)

            # Call the appropriate plot method
            plot_method = getattr(self.view, chart_type)
            result = plot_method(metadata=metadata, stem=output_name, **parameters)

            logger.info(f"✓ Successfully generated chart: {output_name}")
            return result

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise


def create_yaml_directories():
    """Create necessary directories for YAML chart system."""
    yaml_dir = Path("yaml")
    yaml_dir.mkdir(exist_ok=True)

    charts_dir = Path("charts")
    charts_dir.mkdir(exist_ok=True)

    processors_dir = Path("tpsplots/processors")
    processors_dir.mkdir(exist_ok=True)

    # Create __init__.py for processors module
    init_file = processors_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Chart processors module."""\n')


if __name__ == "__main__":
    # Simple command-line test
    import sys
    if len(sys.argv) > 1:
        yaml_path = sys.argv[1]
        processor = YAMLChartProcessor(yaml_path)
        processor.generate_chart()
    else:
        print("Usage: python yaml_chart_processor.py <yaml_file>")