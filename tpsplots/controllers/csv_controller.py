"""CSV file data controller for YAML-driven chart generation."""

import logging

import pandas as pd

from tpsplots.controllers.chart_controller import ChartController
from tpsplots.exceptions import DataSourceError
from tpsplots.utils.currency_processing import clean_currency_column, looks_like_currency_column
from tpsplots.utils.dataframe_transforms import (
    apply_column_cast,
    apply_column_renames,
    filter_columns,
)

logger = logging.getLogger(__name__)


class CSVController(ChartController):
    """
    Controller for processing CSV file data sources.

    This controller provides a standard interface for loading CSV files
    within the YAML chart generation system, while maintaining consistency
    with other controllers that inherit from ChartController.
    """

    def __init__(
        self,
        csv_path: str | None = None,
        cast: dict[str, str] | None = None,
        columns: list[str] | None = None,
        renames: dict[str, str] | None = None,
        auto_clean_currency: bool | None = None,
    ):
        """
        Initialize the CSVController with a CSV file path and optional params.

        Args:
            csv_path: Path to the CSV file to load
            cast: Column type overrides (e.g., {"Date": "datetime", "ID": "str"})
            columns: Columns to keep from the CSV
            renames: Column renames (e.g., {"Old Name": "New Name"})
            auto_clean_currency: Auto-detect and clean currency columns (default True).
                When enabled, columns with 80%+ values matching $X,XXX pattern are
                converted to float64 and originals are preserved as {column}_raw.
        """
        self.csv_path = csv_path
        self.cast = cast
        self.columns = columns
        self.renames = renames
        self.auto_clean_currency = auto_clean_currency if auto_clean_currency is not None else True

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

            # Apply renames first (before column filtering)
            df = apply_column_renames(df, self.renames)

            # Filter to specified columns
            df = filter_columns(df, self.columns, source_name=f"CSV file {self.csv_path}")

            # Apply type casting
            df = apply_column_cast(df, self.cast)

            # Auto-clean currency columns
            if self.auto_clean_currency:
                df = self._clean_currency_columns(df)

            logger.info(
                f"Loaded CSV data from {self.csv_path} ({len(df)} rows, {len(df.columns)} columns)"
            )

            # Use base class method to build result dictionary
            return self._build_result_dict(df)

        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"Error reading CSV file {self.csv_path}: {e}") from e

    def _clean_currency_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-detect and clean currency columns in the DataFrame.

        For columns that appear to contain currency values ($X,XXX format),
        converts them to float64 and preserves the original as {column}_raw.

        Args:
            df: DataFrame to process

        Returns:
            DataFrame with currency columns cleaned
        """
        for col in df.columns:
            if looks_like_currency_column(col, df[col]):
                # Preserve original as _raw
                df[f"{col}_raw"] = df[col]
                # Clean the column
                df[col] = clean_currency_column(df[col])
                logger.debug(f"Cleaned currency column '{col}', original preserved as '{col}_raw'")
        return df

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
                },
            }
        except Exception as e:
            return {"error": f"Could not analyze CSV file: {e}"}
