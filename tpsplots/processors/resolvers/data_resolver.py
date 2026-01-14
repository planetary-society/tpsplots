"""Data source resolution for YAML chart processing."""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Any

from tpsplots.exceptions import DataSourceError
from tpsplots.models.data_sources import (
    ControllerMethodDataSource,
    CSVFileDataSource,
    GoogleSheetsDataSource,
)

logger = logging.getLogger(__name__)


class DataResolver:
    """Resolves data sources from YAML configuration."""

    @staticmethod
    def resolve(
        data_source: ControllerMethodDataSource | CSVFileDataSource | GoogleSheetsDataSource,
    ) -> dict[str, Any]:
        """
        Resolve the data source and return the processed data.

        Args:
            data_source: The data source configuration from YAML

        Returns:
            Dictionary containing the resolved data

        Raises:
            DataSourceError: If data cannot be loaded from the source
        """
        if data_source.type == "controller_method":
            return DataResolver._resolve_controller_method(data_source)
        elif data_source.type == "csv_file":
            return DataResolver._resolve_csv_file(data_source)
        elif data_source.type == "google_sheets":
            return DataResolver._resolve_google_sheets_data(data_source)
        else:
            raise DataSourceError(f"Unsupported data source type: {data_source.type}")

    @staticmethod
    def _resolve_controller_method(
        data_source: ControllerMethodDataSource,
    ) -> dict[str, Any]:
        """Resolve data from a controller method."""
        class_name = data_source.class_name
        method_name = data_source.method

        try:
            if data_source.path:
                controller_class = DataResolver._load_controller_from_path(
                    data_source.path, class_name
                )
            else:
                module_path, resolved_class = DataResolver._split_class_path(class_name)
                module = importlib.import_module(module_path)
                controller_class = getattr(module, resolved_class)

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
                return {"data": result}

        except Exception as e:
            raise DataSourceError(f"Error calling {class_name}.{method_name}: {e}") from e

    @staticmethod
    def _split_class_path(class_path: str) -> tuple[str, str]:
        """Split a fully-qualified class path into module and class name."""
        try:
            if ":" in class_path:
                module_path, class_name = class_path.split(":", 1)
            else:
                module_path, class_name = class_path.rsplit(".", 1)
        except ValueError as e:
            raise DataSourceError(
                f"Invalid class path '{class_path}'. Use 'module.ClassName'."
            ) from e

        if not module_path or not class_name:
            raise DataSourceError(
                f"Invalid class path '{class_path}'. Use 'module.ClassName'."
            )

        return module_path, class_name

    @staticmethod
    def _load_controller_from_path(path: str, class_name: str) -> type:
        """Load a controller class from a Python file path."""
        module_path = Path(path).expanduser().resolve()
        if not module_path.exists():
            raise DataSourceError(f"Controller path not found: {module_path}")
        if module_path.suffix != ".py":
            raise DataSourceError(f"Controller path must be a .py file: {module_path}")

        module_name = f"tpsplots_custom_{module_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise DataSourceError(f"Could not load module from path: {module_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, class_name):
            raise DataSourceError(f"Class '{class_name}' not found in {module_path}")

        return getattr(module, class_name)

    @staticmethod
    def _resolve_csv_file(data_source: CSVFileDataSource) -> dict[str, Any]:
        """Resolve data from a CSV file using CSVController."""
        try:
            from tpsplots.controllers.csv_controller import CSVController

            controller = CSVController(csv_path=data_source.path)
            return controller.load_data()
        except Exception as e:
            raise DataSourceError(f"Error loading CSV data: {e}") from e

    @staticmethod
    def _resolve_google_sheets_data(data_source: GoogleSheetsDataSource) -> dict[str, Any]:
        """Resolve data from Google Sheets or URL using GoogleSheetsController."""
        try:
            from tpsplots.controllers.google_sheets_controller import GoogleSheetsController

            controller = GoogleSheetsController(url=data_source.url)
            return controller.load_data()
        except Exception as e:
            raise DataSourceError(f"Error loading Google Sheets data: {e}") from e
