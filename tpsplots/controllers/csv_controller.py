"""CSV file data controller for YAML-driven chart generation."""

import logging

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.csv_source import CSVSource
from tpsplots.exceptions import DataSourceError

logger = logging.getLogger(__name__)


class CSVController(ChartController):
    """
    Controller for processing CSV file data sources.

    This controller delegates all data loading and processing to
    :class:`~tpsplots.data_sources.csv_source.CSVSource`, providing a
    standard controller interface for the YAML chart generation system.
    """

    def __init__(
        self,
        csv_path: str | None = None,
        cast: dict[str, str] | None = None,
        columns: list[str] | None = None,
        renames: dict[str, str] | None = None,
        auto_clean_currency: bool | dict | None = None,
        fiscal_year_column: str | bool | None = None,
    ):
        """
        Initialize the CSVController with a CSV file path and optional params.

        Args:
            csv_path: Path to the CSV file to load
            cast: Column type overrides (e.g., {"Date": "datetime", "ID": "str"})
            columns: Columns to keep from the CSV
            renames: Column renames (e.g., {"Old Name": "New Name"})
            auto_clean_currency: Auto-detect and clean currency columns (default True).
                Can be bool or dict with 'enabled' (bool) and 'multiplier' (float) keys.
                When enabled, columns with 80%+ values matching $X,XXX pattern are
                converted to float64 and originals are preserved as {column}_raw.
            fiscal_year_column: Column to convert to datetime (default auto-detect).
                - None: Auto-detect columns named "Fiscal Year", "FY", or "Year"
                - str: Use this specific column name
                - False: Disable fiscal year conversion
        """
        self.csv_path = csv_path
        self.cast = cast
        self.columns = columns
        self.renames = renames
        self.auto_clean_currency = auto_clean_currency if auto_clean_currency is not None else True
        self.fiscal_year_column = fiscal_year_column
        self._source = None

    def load_data(self):
        """
        Load data from CSV file and return as dict for YAML processing.

        Delegates to :class:`CSVSource` for reading and processing,
        then wraps the result using base-class helpers.

        Returns:
            dict: Dictionary containing:
                - 'data': Full pandas DataFrame (for export_data)
                - Individual column keys: Column data as numpy arrays
                - '{column}_year' keys: Rounded year integers for date columns

        Raises:
            ValueError: If csv_path is not provided
            DataSourceError: If CSV file cannot be read
        """
        if not self.csv_path:
            raise ValueError("csv_path must be provided to load CSV data")

        try:
            # Build source kwargs from non-None params
            source_kwargs = {}
            if self.cast:
                source_kwargs["cast"] = self.cast
            if self.columns:
                source_kwargs["columns"] = self.columns
            if self.renames:
                source_kwargs["renames"] = self.renames
            if self.auto_clean_currency is not None:
                source_kwargs["auto_clean_currency"] = self.auto_clean_currency
            if self.fiscal_year_column is not None:
                source_kwargs["fiscal_year_column"] = self.fiscal_year_column

            self._source = CSVSource(csv_path=self.csv_path, **source_kwargs)
            df = self._source.data()

            logger.info(
                f"Loaded CSV data from {self.csv_path} ({len(df)} rows, {len(df.columns)} columns)"
            )

            # Use base class method to build result dictionary
            result = self._build_result_dict(df)
            result["metadata"] = self._build_metadata(df)
            return result

        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"Error reading CSV file {self.csv_path}: {e}") from e

    def get_data_summary(self):
        """
        Get a summary of the loaded data for debugging purposes.

        Returns:
            dict: Summary information about the loaded data
        """
        if not self.csv_path:
            return {"error": "No CSV path specified"}

        try:
            df = pd.read_csv(self.csv_path)
            return {
                "file_path": self.csv_path,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict("records"),
                "configuration": {
                    "cast": self.cast,
                    "columns": self.columns,
                    "renames": self.renames,
                    "auto_clean_currency": self.auto_clean_currency,
                    "fiscal_year_column": self.fiscal_year_column,
                },
            }
        except Exception as e:
            return {"error": f"Could not analyze CSV file: {e}"}
