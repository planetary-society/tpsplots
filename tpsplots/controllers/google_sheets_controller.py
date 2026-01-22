"""Google Sheets data controller for YAML-driven chart generation."""

import logging
import re

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.exceptions import DataSourceError
from tpsplots.utils.date_processing import looks_like_date_column, round_date_to_year

logger = logging.getLogger(__name__)


class GoogleSheetsController(ChartController):
    """
    Controller for processing Google Sheets data sources using GoogleSheetsSource.

    This controller wraps the existing GoogleSheetsSource class to provide
    a standard controller interface for the YAML chart generation system,
    while leveraging all the features of GoogleSheetsSource (column selection,
    type casting, etc.).
    """

    def __init__(
        self,
        url: str | None = None,
        cast: dict[str, str] | None = None,
        columns: list[str] | None = None,
        renames: dict[str, str] | None = None,
    ):
        """
        Initialize the GoogleSheetsController with URL and options.

        Args:
            url: Google Sheets URL (can be regular URL or CSV export URL)
            cast: Column type overrides (e.g., {"Date": "datetime", "ID": "str"})
            columns: Columns to keep from the sheet
            renames: Column renames (e.g., {"Old Name": "New Name"})
        """
        self.url = url
        self.cast = cast
        self.columns = columns
        self.renames = renames
        self._source = None

    def load_data(self):
        """
        Load data from Google Sheets and return as dict for YAML processing.

        Returns:
            dict: Dictionary containing:
                - 'data': Full pandas DataFrame (for export_data)
                - Individual column keys: Column data as numpy arrays
                - '{column}_year' keys: Rounded year integers for date columns

        Raises:
            ValueError: If URL is not provided
            RuntimeError: If data cannot be fetched from URL
        """
        if not self.url:
            raise ValueError("url must be provided to load Google Sheets data")

        try:
            # Create GoogleSheetsSource with all parameters
            source_kwargs = {}
            if self.cast:
                source_kwargs["cast"] = self.cast
            if self.columns:
                source_kwargs["columns"] = self.columns
            if self.renames:
                source_kwargs["renames"] = self.renames

            self._source = GoogleSheetsSource(url=self.url, **source_kwargs)
            df = self._source.data()

            logger.info(
                f"Loaded Google Sheets data from {self.url} ({len(df)} rows, {len(df.columns)} columns)"
            )

            # Build result dictionary with multiple access patterns
            result = {"data": df}  # Keep full DataFrame for export_data

            # Expose each column as a top-level key for YAML parameter resolution
            for col in df.columns:
                result[col] = df[col].values

                # Auto-detect date columns and create _year variants with mid-year rounding
                if looks_like_date_column(col, df[col]):
                    try:
                        dt_series = pd.to_datetime(df[col], errors="coerce")
                        year_col_name = f"{col}_year"
                        result[year_col_name] = round_date_to_year(dt_series).values
                        logger.debug(f"Created year column '{year_col_name}' from '{col}'")
                    except Exception as e:
                        logger.debug(f"Could not convert '{col}' to years: {e}")

            return result

        except Exception as e:
            raise DataSourceError(
                f"Error fetching data from Google Sheets URL {self.url}: {e}"
            ) from e

    def get_data_summary(self):
        """
        Get a summary of the loaded data for debugging purposes.

        Returns:
            dict: Summary information about the loaded data
        """
        if not self.url:
            return {"error": "No URL specified"}

        try:
            if not self._source:
                # Create source if not already created
                self.load_data()

            df = self._source.data()
            return {
                "url": self.url,
                "rows": len(df),
                "columns": list(df.columns),
                "dtypes": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict("records"),
                "configuration": {
                    "cast": self.cast,
                    "columns": self.columns,
                    "renames": self.renames,
                },
            }
        except Exception as e:
            return {"error": f"Could not analyze Google Sheets data: {e}"}

    def get_column_data(self, column_name: str):
        """
        Get data from a specific column using GoogleSheetsSource's attribute access.

        Args:
            column_name: Name of the column to retrieve

        Returns:
            List of values from the specified column
        """
        if not self._source:
            self.load_data()

        return getattr(self._source, column_name.lower().replace(" ", "_"))

    @staticmethod
    def normalize_google_sheets_url(url: str) -> str:
        """
        Convert a regular Google Sheets URL to CSV export format.

        Args:
            url: Google Sheets URL (regular or export format)

        Returns:
            str: CSV export URL
        """
        if "docs.google.com/spreadsheets" in url and "export?format=csv" not in url:
            # Extract sheet ID and convert to CSV export URL
            sheet_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
            if sheet_id_match:
                sheet_id = sheet_id_match.group(1)
                return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

        return url
