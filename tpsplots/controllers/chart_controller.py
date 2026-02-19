"""tpsplots.base - shared chart infrastructure"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class ChartController:
    """
    Base class for chart controllers in the MVC pattern.

    This class provides shared utilities for data preparation and formatting.
    Subclasses implement methods that return data dictionaries for YAML-driven
    chart generation.
    """

    def _build_result_dict(self, df: pd.DataFrame) -> dict[str, Any]:
        """Build standard result dictionary from DataFrame.

        Creates a consistent output format for YAML parameter resolution:
        - 'data': Full DataFrame for export_data
        - Column names: numpy arrays for direct access
        - '{column}_year': Year extraction for date columns

        Args:
            df: DataFrame containing the loaded data

        Returns:
            dict: Result dictionary with multiple access patterns
        """
        from tpsplots.utils.date_processing import looks_like_date_column, round_date_to_year

        result: dict[str, Any] = {"data": df}

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

    def _get_rounded_axis_limit_y(
        self, max_value: float, multiple: float = 5000000000, always_extend: bool = True
    ) -> float:
        """
        Returns a reasonable upper boundary for the y-axis based on the maximum value in the data.

        This method rounds up the maximum value to the next multiple of the specified value,
        ensuring clean and consistent y-axis limits for charts, particularly for financial data.

        Example: For a maximum value of $23.7 billion and a multiple of $5 billion,
        this returns $25 billion.

        Args:
            max_value (float): The maximum value in the dataset
            multiple (float): The value to round up to. Defaults to 5 billion ($5,000,000,000)
            always_extend (bool): When True, ensures the limit is at least one multiple
                                higher than the max_value. When False, only extends if needed.
                                Defaults to True to provide headroom in charts.

        Returns:
            float: The rounded upper limit suitable for y-axis plotting
        """
        # If max_value is less than multiple, just return multiple for a cleaner chart
        if max_value < multiple:
            return multiple

        # Calculate how many whole multiples fit into max_value
        whole_multiples = max_value // multiple

        # Check if max_value is exactly at a multiple boundary
        if max_value % multiple == 0:
            # If always_extend is True or we're exactly at a boundary, add a full multiple
            return (whole_multiples + 1) * multiple if always_extend else max_value

        # Otherwise, round up to the next multiple
        return (whole_multiples + 1) * multiple

    def _get_rounded_axis_limit_x(
        self, upper_value: int, multiple: int = 10, always_extend: bool = False
    ) -> int:
        """Returns the next highest integer divisible by the multiple given a
        beyond the given upper_value

        Example: If we have data through FY 2026, and we want the next highest year that is
        divisible by 10, the method will return 2030.

        This is helpful for ensuring clean and consistent x-axes for charts.

        Args:
            upper_value (int): End point for fiscal year with actual data
            multiple (int): The multiplier. Defaults to 10.
            always_extend (bool): When True, always adds at least one multiple beyond upper_value,
                                even if upper_value already falls on a multiple boundary.
                                When False, only extends if needed.

        Returns:
            int: The next year after upper_value where % multiple == 0
        """
        # Find the remainder
        remainder = upper_value % multiple

        # If the remainder is 0, upper_value is already at a multiple boundary
        if remainder == 0:
            # If always_extend is True or we're on a boundary, add a full multiple
            return upper_value + multiple if always_extend else upper_value

        # Otherwise, add the difference needed to reach the next multiple boundary
        return upper_value + (multiple - remainder)

    def _export_helper(
        self, original_df: pd.DataFrame, columns_to_export: list[str]
    ) -> pd.DataFrame:
        """Helper method to prepare columns for export, assuming it will mostly be Fiscal Year and dollar amounts"""
        export_df = original_df[columns_to_export].copy().reset_index(drop=True)

        if "Fiscal Year" in columns_to_export:
            try:
                export_df["Fiscal Year"] = pd.to_datetime(export_df["Fiscal Year"]).dt.strftime(
                    "%Y"
                )
            except Exception:
                export_df["Fiscal Year"] = export_df["Fiscal Year"].astype(
                    str
                )  # Fallback to string

        for col in columns_to_export:
            if col == "Fiscal Year":
                continue
            numeric_series = pd.to_numeric(export_df[col], errors="coerce")
            export_df[col] = numeric_series.round(0)
        return export_df

    def _build_metadata(
        self,
        df: pd.DataFrame,
        fiscal_year_col: str = "Fiscal Year",
        value_columns: dict[str, str] | None = None,
    ) -> dict:
        """Build a consistent metadata dict with helpful context for YAML templates.

        This method extracts common metadata from a DataFrame, including min/max
        fiscal years for the overall dataset and for specific value columns.

        Args:
            df: DataFrame containing the data
            fiscal_year_col: Name of the fiscal year column (default "Fiscal Year")
            value_columns: Dict mapping output names to column names for per-column
                          fiscal year calculations. E.g., {"appropriation": "Appropriation"}
                          will generate max_appropriation_fiscal_year and
                          min_appropriation_fiscal_year.

        Returns:
            dict with metadata keys:
                - max_fiscal_year: int - Maximum fiscal year in dataset
                - min_fiscal_year: int - Minimum fiscal year in dataset
                - max_{name}_fiscal_year: int - Max FY with non-null data for each value_column
                - min_{name}_fiscal_year: int - Min FY with non-null data for each value_column

        Example usage in YAML:
            title: "NASA Budget {{metadata.min_fiscal_year}}-{{metadata.max_appropriation_fiscal_year}}"
        """
        metadata = {}

        # Convert fiscal year to datetime if needed
        fy_series = df[fiscal_year_col]
        if not pd.api.types.is_datetime64_any_dtype(fy_series):
            fy_series = pd.to_datetime(fy_series)

        # Overall min/max fiscal year
        metadata["max_fiscal_year"] = int(fy_series.max().strftime("%Y"))
        metadata["min_fiscal_year"] = int(fy_series.min().strftime("%Y"))

        # Per-column fiscal year ranges (only for rows with non-null values)
        if value_columns:
            for name, col in value_columns.items():
                if col in df.columns:
                    # Get rows where this column has data
                    mask = df[col].notna()
                    if mask.any():
                        col_fy = fy_series[mask]
                        metadata[f"max_{name}_fiscal_year"] = int(col_fy.max().strftime("%Y"))
                        metadata[f"min_{name}_fiscal_year"] = int(col_fy.min().strftime("%Y"))

        return metadata

    @staticmethod
    def round_to_millions(amount: float) -> str:
        """Format money amount with commas and 2 decimal places, display as millions or billions based on the amount."""
        if amount < 0:
            is_neg = True
            amount = amount * -1
        else:
            is_neg = False

        if amount >= 1_000_000_000:
            formatted = f"${amount / 1_000_000_000:,.0f} billion"
        elif amount >= 10_000_000 or amount >= 1_000_000:
            formatted = f"${amount / 1_000_000:,.0f} million"
        else:
            formatted = f"${amount:,.2f}"

        if is_neg:
            formatted = "-" + formatted

        return formatted
