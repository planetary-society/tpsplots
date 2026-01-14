"""Data source resolution for YAML chart processing."""

import importlib
import logging
import re
from pathlib import Path
from typing import Any

from tpsplots.exceptions import DataSourceError
from tpsplots.models.data_sources import (
    ControllerMethodDataSource,
    CSVFileDataSource,
    URLDataSource,
)

logger = logging.getLogger(__name__)


class DataResolver:
    """Resolves data sources from YAML configuration."""

    @staticmethod
    def resolve(
        data_source: ControllerMethodDataSource | CSVFileDataSource | URLDataSource,
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
        elif data_source.type in ["google_sheets", "url"]:
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
            # Dynamic import of controller class
            # First try from tpsplots.controllers
            try:
                module_path = f"tpsplots.controllers.{DataResolver._snake_case(class_name)}"
                module = importlib.import_module(module_path)
                controller_class = getattr(module, class_name)
            except (ImportError, AttributeError):
                # Fallback: try to find the class in any controllers module
                controller_class = DataResolver._find_controller_class(class_name)

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
    def _find_controller_class(class_name: str) -> type:
        """Find controller class by searching all controller modules."""
        controllers_dir = Path(__file__).parent.parent.parent / "controllers"

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

        raise DataSourceError(f"Could not find controller class '{class_name}'")

    @staticmethod
    def _snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

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
    def _resolve_google_sheets_data(data_source: URLDataSource) -> dict[str, Any]:
        """Resolve data from Google Sheets or URL using GoogleSheetsController."""
        try:
            from tpsplots.controllers.google_sheets_controller import GoogleSheetsController

            controller = GoogleSheetsController(url=data_source.url)
            return controller.load_data()
        except Exception as e:
            raise DataSourceError(f"Error loading Google Sheets data: {e}") from e
