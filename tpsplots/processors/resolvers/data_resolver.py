"""Data source resolution for YAML chart processing (v2.0 spec)."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Any

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.exceptions import DataSourceError
from tpsplots.models.data_sources import DataSourceConfig

logger = logging.getLogger(__name__)


class DataResolver:
    """Resolves data sources from YAML configuration."""

    @staticmethod
    def resolve(data_source: DataSourceConfig) -> dict[str, Any]:
        """
        Resolve the data source and return the processed data.

        Args:
            data_source: The data source configuration from YAML

        Returns:
            Dictionary containing the resolved data

        Raises:
            DataSourceError: If data cannot be loaded from the source
        """
        source = data_source.source.strip()
        if not source:
            raise DataSourceError("Data source 'source' must not be empty")

        kind, target, method = DataResolver._parse_source(source)

        if kind == "url":
            return DataResolver._resolve_url(target)
        if kind == "csv":
            return DataResolver._resolve_csv(target)
        if kind == "controller_module":
            return DataResolver._resolve_controller_module(target, method)
        if kind == "controller_path":
            return DataResolver._resolve_controller_path(target, method)

        raise DataSourceError(f"Unsupported data source: {source}")

    @staticmethod
    def _parse_source(source: str) -> tuple[str, str, str | None]:
        """Parse a source string into a (kind, target, method) tuple."""
        source = source.strip()

        prefix = None
        for candidate in ("controller:", "csv:", "url:"):
            if source.lower().startswith(candidate):
                prefix = candidate[:-1]
                source = source[len(candidate) :].strip()
                break

        if not source:
            raise DataSourceError("Data source 'source' must not be empty")

        if prefix == "url":
            return "url", source, None
        if prefix == "csv":
            return "csv", source, None
        if prefix == "controller":
            if ".py:" in source:
                path, method = source.rsplit(":", 1)
                method = method.strip()
                if not method:
                    raise DataSourceError(
                        "Custom controller source must include a method name: "
                        "'/path/to/controller.py:method_name'"
                    )
                return "controller_path", path.strip(), method
            if source.endswith(".py"):
                raise DataSourceError(
                    "Custom controller source must include a method name: "
                    "'/path/to/controller.py:method_name'"
                )
            return DataResolver._parse_controller_source(source)

        if source.startswith("http://") or source.startswith("https://"):
            return "url", source, None

        if ".py:" in source:
            path, method = source.rsplit(":", 1)
            method = method.strip()
            if not method:
                raise DataSourceError(
                    "Custom controller source must include a method name: "
                    "'/path/to/controller.py:method_name'"
                )
            return "controller_path", path.strip(), method
        if source.endswith(".py"):
            raise DataSourceError(
                "Custom controller source must include a method name: "
                "'/path/to/controller.py:method_name'"
            )

        if "/" in source or "\\" in source or source.endswith(".csv"):
            return "csv", source, None

        return DataResolver._parse_controller_source(source)

    @staticmethod
    def _parse_controller_source(source: str) -> tuple[str, str, str]:
        """Parse a controller source string into module and method."""
        if "." not in source:
            raise DataSourceError(
                "Controller source must be in 'module.method' format "
                "(e.g., nasa_budget_chart.nasa_budget_by_year)"
            )
        module_name, method_name = source.rsplit(".", 1)
        module_name = module_name.strip()
        method_name = method_name.strip()
        if not module_name or not method_name:
            raise DataSourceError(
                "Controller source must be in 'module.method' format "
                "(e.g., nasa_budget_chart.nasa_budget_by_year)"
            )
        return "controller_module", module_name, method_name

    @staticmethod
    def _resolve_controller_module(module_name: str, method_name: str) -> dict[str, Any]:
        """Resolve data from a controller method within tpsplots.controllers."""
        try:
            module = importlib.import_module(f"tpsplots.controllers.{module_name}")
        except Exception as e:
            raise DataSourceError(f"Could not import controller module '{module_name}': {e}") from e

        controller_class = DataResolver._find_controller_class(
            module, method_name, f"tpsplots.controllers.{module_name}"
        )
        return DataResolver._call_controller_method(controller_class, method_name)

    @staticmethod
    def _resolve_controller_path(path: str, method_name: str) -> dict[str, Any]:
        """Resolve data from a controller method in a local Python file."""
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

        controller_class = DataResolver._find_controller_class(module, method_name, str(module_path))
        return DataResolver._call_controller_method(controller_class, method_name)

    @staticmethod
    def _find_controller_class(module: Any, method_name: str, source_label: str) -> type:
        """Find the unique ChartController subclass that implements the method."""
        candidates = []
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if not issubclass(obj, ChartController) or obj is ChartController:
                continue
            if callable(getattr(obj, method_name, None)):
                candidates.append(obj)

        if not candidates:
            raise DataSourceError(
                f"No ChartController with method '{method_name}' found in {source_label}"
            )
        if len(candidates) > 1:
            class_names = ", ".join(cls.__name__ for cls in candidates)
            raise DataSourceError(
                f"Multiple controller classes in {source_label} implement '{method_name}': "
                f"{class_names}. Each controller file must contain a single ChartController "
                f"subclass with that method."
            )

        return candidates[0]

    @staticmethod
    def _call_controller_method(controller_class: type, method_name: str) -> dict[str, Any]:
        """Call a controller method and validate the return type."""
        controller = controller_class()

        try:
            result = getattr(controller, method_name)()
            logger.info(
                "Retrieved data from %s.%s", controller_class.__name__, method_name
            )
        except Exception as e:
            raise DataSourceError(
                f"Error calling {controller_class.__name__}.{method_name}: {e}"
            ) from e

        if not isinstance(result, dict):
            raise DataSourceError(
                f"{controller_class.__name__}.{method_name} must return a dict of values"
            )

        return result

    @staticmethod
    def _resolve_csv(path: str) -> dict[str, Any]:
        """Resolve data from a CSV file using CSVController."""
        try:
            from tpsplots.controllers.csv_controller import CSVController

            controller = CSVController(csv_path=path)
            return controller.load_data()
        except Exception as e:
            raise DataSourceError(f"Error loading CSV data: {e}") from e

    @staticmethod
    def _resolve_url(url: str) -> dict[str, Any]:
        """Resolve data from a URL (Google Sheets, direct CSV, etc.)."""
        try:
            from tpsplots.controllers.google_sheets_controller import GoogleSheetsController

            controller = GoogleSheetsController(url=url)
            return controller.load_data()
        except Exception as e:
            raise DataSourceError(f"Error loading URL data: {e}") from e
