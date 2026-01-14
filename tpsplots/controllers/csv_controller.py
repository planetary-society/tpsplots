"""CSV file data controller for YAML-driven chart generation."""

import logging
import re

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController

logger = logging.getLogger(__name__)


class CSVController(ChartController):
    """
    Controller for processing CSV file data sources.

    This controller provides a standard interface for loading CSV files
    within the YAML chart generation system, while maintaining consistency
    with other controllers that inherit from ChartController.
    """

    def __init__(self, csv_path: str | None = None):
        """
        Initialize the CSVController with a CSV file path.

        Args:
            csv_path: Path to the CSV file to load
        """
        super().__init__()
        self.csv_path = csv_path

    def load_data(self):
        """
        Load data from CSV file and return as dict for YAML processing.

        Returns:
            dict: Dictionary containing:
                - 'data': Full pandas DataFrame (for export_data)
                - Individual column keys: Column data as numpy arrays
                - '{column}_year' keys: Rounded year integers for date columns

        Raises:
            ValueError: If csv_path is not provided
            RuntimeError: If CSV file cannot be read
        """
        if not self.csv_path:
            raise ValueError("csv_path must be provided to load CSV data")

        try:
            df = pd.read_csv(self.csv_path)
            logger.info(
                f"Loaded CSV data from {self.csv_path} ({len(df)} rows, {len(df.columns)} columns)"
            )

            # Build result dictionary with multiple access patterns
            result = {"data": df}  # Keep full DataFrame for export_data

            # Expose each column as a top-level key for YAML parameter resolution
            for col in df.columns:
                result[col] = df[col].values

                # Auto-detect date columns and create _year variants with mid-year rounding
                if self._looks_like_date_column(col, df[col]):
                    try:
                        dt_series = pd.to_datetime(df[col], errors="coerce")
                        year_col_name = f"{col}_year"
                        result[year_col_name] = self._round_date_to_year(dt_series).values
                        logger.debug(f"Created year column '{year_col_name}' from '{col}'")
                    except Exception as e:
                        logger.debug(f"Could not convert '{col}' to years: {e}")

            return result

        except Exception as e:
            raise RuntimeError(f"Error reading CSV file {self.csv_path}: {e}") from e

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
            }
        except Exception as e:
            return {"error": f"Could not analyze CSV file: {e}"}

    def _looks_like_date_column(self, col_name: str, series: pd.Series) -> bool:
        """
        Check if a column contains date-like data.

        Args:
            col_name: Column name
            series: Pandas Series to check

        Returns:
            bool: True if the column appears to contain dates
        """
        if len(series) == 0:
            return False

        # Get first non-null value
        first_val = series.dropna().iloc[0] if len(series.dropna()) > 0 else None
        if first_val is None:
            return False

        # Check if value matches date format (YYYY-MM-DD)
        # This catches both explicit date columns and implicit ones like "First Crewed Utilization"
        return bool(re.match(r"\d{4}-\d{2}-\d{2}", str(first_val)))

    def _round_date_to_year(self, dt_series: pd.Series) -> pd.Series:
        """
        Round dates to nearest year using June 15 cutoff.

        Dates before June 15 round to the current year.
        Dates on or after June 15 round to the next year.

        Args:
            dt_series: Pandas Series of datetime objects

        Returns:
            pd.Series: Series of integer years

        Examples:
            1959-01-09 → 1959 (before June 15)
            1959-06-14 → 1959 (before June 15)
            1959-06-15 → 1960 (at cutoff, rounds up)
            1961-12-07 → 1962 (after June 15)
        """

        def round_single_date(dt):
            if pd.isna(dt):
                return pd.NA
            # Check if before June 15 (month < 6, or month == 6 and day < 15)
            if dt.month < 6 or (dt.month == 6 and dt.day < 15):
                return dt.year
            else:
                return dt.year + 1

        return dt_series.apply(round_single_date)
