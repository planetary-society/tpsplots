"""tpsplots.base - shared chart infrastructure"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from tpsplots.data_sources.fiscal_year_mixin import FiscalYearMixin

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

    @staticmethod
    def _resolve_fiscal_year_metadata_column(
        df: pd.DataFrame,
        fiscal_year_column: str | bool | None = None,
    ) -> str | None:
        """Resolve which fiscal-year column metadata extraction should use.

        Mirrors the tabular source behavior:
        - ``False`` disables FY metadata extraction.
        - ``str`` uses the configured column directly.
        - ``None`` auto-detects columns like ``Fiscal Year``, ``FY``, or ``Year``.
        """
        if fiscal_year_column is False:
            return None
        if isinstance(fiscal_year_column, str):
            return fiscal_year_column
        return FiscalYearMixin._detect_fy_column(df)

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
        self,
        original_df: pd.DataFrame,
        columns_to_export: list[str],
        rounding: dict[str, int] | None = None,
    ) -> pd.DataFrame:
        """Prepare columns for export with per-column rounding control.

        Args:
            original_df: Source DataFrame.
            columns_to_export: Column names to include in the export.
            rounding: Optional dict mapping column names to decimal precision.
                Columns not listed default to ``round(2)``.  Pass e.g.
                ``{"YOY % FTE Change": 4}`` to keep four decimal places.
        """
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
            if numeric_series.isna().all():
                continue  # Skip purely non-numeric columns (e.g. labels)
            precision = rounding.get(col, 2) if rounding else 2
            export_df[col] = numeric_series.round(precision)
        return export_df

    def _build_metadata(
        self,
        df: pd.DataFrame,
        *,
        fiscal_year_col: str | None = "Fiscal Year",
        value_columns: dict[str, str] | None = None,
        source: str | None = None,
        max_fiscal_year: int | None = None,
        min_fiscal_year: int | None = None,
    ) -> dict:
        """Build a consistent metadata dict with helpful context for YAML templates.

        This method extracts common metadata from a DataFrame, including min/max
        fiscal years for the overall dataset, per-column fiscal year ranges, value
        statistics, inflation metadata, and source attribution.

        Args:
            df: DataFrame containing the data
            fiscal_year_col: Name of the fiscal year column (default "Fiscal Year").
                Set to None to skip FY extraction entirely.
            value_columns: Dict mapping output names to column names for per-column
                          fiscal year calculations and value statistics. E.g.,
                          {"appropriation": "Appropriation"} will generate
                          max_appropriation_fiscal_year, min_appropriation_fiscal_year,
                          max_appropriation, and min_appropriation.
            source: Source attribution string (e.g., "NASA Budget Justifications").
            max_fiscal_year: Explicit override for max_fiscal_year (takes precedence
                over DataFrame extraction).
            min_fiscal_year: Explicit override for min_fiscal_year (takes precedence
                over DataFrame extraction).

        Returns:
            dict with metadata keys:
                - max_fiscal_year: int - Maximum fiscal year in dataset
                - min_fiscal_year: int - Minimum fiscal year in dataset
                - max_{name}_fiscal_year: int - Max FY with non-null data for each value_column
                - min_{name}_fiscal_year: int - Min FY with non-null data for each value_column
                - max_{name}: float - Max value for each value_column
                - min_{name}: float - Min value for each value_column
                - inflation_adjusted_year: int - Target year for inflation adjustment
                - source: str - Source attribution

        Example usage in YAML:
            title: "NASA Budget {{metadata.min_fiscal_year}}-{{metadata.max_appropriation_fiscal_year}}"
        """
        metadata: dict = {}

        # 1. Extract FY ranges from DataFrame (if column exists)
        fy_series = None
        if fiscal_year_col is not None and fiscal_year_col in df.columns:
            fy_series = df[fiscal_year_col]
            if pd.api.types.is_integer_dtype(fy_series):
                metadata["max_fiscal_year"] = int(fy_series.max())
                metadata["min_fiscal_year"] = int(fy_series.min())
            elif pd.api.types.is_datetime64_any_dtype(fy_series):
                metadata["max_fiscal_year"] = int(fy_series.max().strftime("%Y"))
                metadata["min_fiscal_year"] = int(fy_series.min().strftime("%Y"))
            else:
                fy_series = pd.to_datetime(fy_series)
                metadata["max_fiscal_year"] = int(fy_series.max().strftime("%Y"))
                metadata["min_fiscal_year"] = int(fy_series.min().strftime("%Y"))

        # 2. Per-column fiscal year ranges and value statistics
        if value_columns and fy_series is not None:
            for name, col in value_columns.items():
                if col in df.columns:
                    mask = df[col].notna()
                    if mask.any():
                        col_fy = fy_series[mask]
                        if pd.api.types.is_integer_dtype(df[fiscal_year_col]):
                            metadata[f"max_{name}_fiscal_year"] = int(col_fy.max())
                            metadata[f"min_{name}_fiscal_year"] = int(col_fy.min())
                        else:
                            metadata[f"max_{name}_fiscal_year"] = int(col_fy.max().strftime("%Y"))
                            metadata[f"min_{name}_fiscal_year"] = int(col_fy.min().strftime("%Y"))
                        metadata[f"max_{name}"] = float(df[col][mask].max())
                        metadata[f"min_{name}"] = float(df[col][mask].min())

        # 3. Apply explicit FY overrides
        if max_fiscal_year is not None:
            metadata["max_fiscal_year"] = max_fiscal_year
        if min_fiscal_year is not None:
            metadata["min_fiscal_year"] = min_fiscal_year

        # 4. Extract inflation metadata from DataFrame attrs
        self._add_inflation_adjusted_year_metadata(metadata, df)

        # 5. Set source
        if source is not None:
            metadata["source"] = source

        return metadata

    @staticmethod
    def _add_inflation_adjusted_year_metadata(
        metadata: dict[str, int | str],
        df: pd.DataFrame,
    ) -> dict[str, int | str]:
        """Populate metadata with inflation-adjusted target fiscal year.

        Kept as standalone for controllers that build metadata without
        ``_build_metadata``.
        """
        if "inflation_target_year" in df.attrs:
            metadata["inflation_adjusted_year"] = int(df.attrs["inflation_target_year"])
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
