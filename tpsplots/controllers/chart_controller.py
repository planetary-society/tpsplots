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
                except (ValueError, KeyError, TypeError, AttributeError) as e:
                    logger.debug(f"Could not convert '{col}' to years: {e}")

        return result

    def _build_load_result(
        self,
        df: pd.DataFrame,
        fiscal_year_column: str | bool | None = None,
    ) -> dict[str, Any]:
        """Build the standard result dict from a loaded DataFrame.

        Shared post-load pipeline used by generic data controllers (CSV,
        Google Sheets).  Column sums are computed later by
        :meth:`DataResolver._compute_column_sums` so that calculated columns
        (e.g. inflation-adjusted series) are included.

        Args:
            df: Loaded DataFrame from the data source.
            fiscal_year_column: Forwarded to
                :meth:`_resolve_fiscal_year_metadata_column`.

        Returns:
            dict with ``data``, per-column arrays, and ``metadata`` keys.
        """
        fy_col = self._resolve_fiscal_year_metadata_column(df, fiscal_year_column)
        value_columns = df.attrs.get("value_columns")
        result = self._build_result_dict(df)
        result["metadata"] = self._build_metadata(
            df,
            fiscal_year_col=fy_col,
            value_columns=value_columns,
        )
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

    # TODO: Consolidate _export_helper logic (FY formatting, per-column rounding)
    # into DataFrameToYAMLProcessor so controllers don't need to build export_df
    # separately. Currently used by NASABudgetChart and ApolloController.
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
            except (ValueError, TypeError):
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
                          max_appropriation, min_appropriation,
                          first_appropriation, and last_appropriation.
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
                - first_{name}: float - First non-null value for each value_column
                - last_{name}: float - Last non-null value for each value_column
                - inflation_adjusted_year: int - Target year for inflation adjustment
                - source: str - Source attribution

        Example usage in YAML:
            title: "NASA Budget {{metadata.min_fiscal_year}}-{{metadata.max_appropriation_fiscal_year}}"
        """
        metadata: dict = {}

        # 1. Extract FY ranges from DataFrame (if column exists)
        fy_years = None
        if fiscal_year_col is not None and fiscal_year_col in df.columns:
            # Handles datetime, integer, and fiscal-period label columns
            # (including NASA's 1976 transition quarter).
            fy_years = FiscalYearMixin._fy_years(df[fiscal_year_col])

            valid_fy_years = fy_years.dropna()
            if not valid_fy_years.empty:
                metadata["max_fiscal_year"] = int(valid_fy_years.max())
                metadata["min_fiscal_year"] = int(valid_fy_years.min())

        # 2. Per-column fiscal year ranges and value statistics
        if value_columns and fy_years is not None:
            for name, col in value_columns.items():
                if col in df.columns:
                    mask = df[col].notna()
                    if mask.any():
                        col_values = df.loc[mask, col]
                        col_fy = fy_years[mask].dropna()
                        if not col_fy.empty:
                            metadata[f"max_{name}_fiscal_year"] = int(col_fy.max())
                            metadata[f"min_{name}_fiscal_year"] = int(col_fy.min())
                        metadata[f"max_{name}"] = float(col_values.max())
                        metadata[f"min_{name}"] = float(col_values.min())
                        metadata[f"first_{name}"] = float(col_values.iloc[0])
                        metadata[f"last_{name}"] = float(col_values.iloc[-1])

        # 3. Apply explicit FY overrides
        if max_fiscal_year is not None:
            metadata["max_fiscal_year"] = max_fiscal_year
        if min_fiscal_year is not None:
            metadata["min_fiscal_year"] = min_fiscal_year

        # 4. Extract inflation metadata from DataFrame attrs
        self._add_inflation_adjusted_year_metadata(metadata, df)

        # 4.5 Column sums written by ColumnSumProcessor
        column_sums: dict = df.attrs.get("column_sums", {})
        if column_sums:
            metadata["column_sums"] = column_sums

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
