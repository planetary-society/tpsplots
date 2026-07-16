"""Mixin for fiscal year detection and datetime conversion."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

# Pattern matches: "Fiscal Year", "FY", "FY2024", "Year" (case-insensitive)
FY_COLUMN_PATTERN = re.compile(r"^(fiscal\s*year|fy\d{0,4}|year)$", re.IGNORECASE)

# Year embedded in a fiscal-period label, e.g. "1976 TQ" or "FY2024"
FY_YEAR_PATTERN = re.compile(r"(\d{4})")


class FiscalYearMixin:
    """
    Mixin providing fiscal year column detection and datetime conversion.

    Auto-detects columns matching FY patterns, casts to int, and converts
    to datetime objects (Jan 1 of that year) for proper matplotlib axis handling.
    """

    @staticmethod
    def _detect_fy_column(df: pd.DataFrame) -> str | None:
        """Detect fiscal year column by name pattern."""
        for col in df.columns:
            if FY_COLUMN_PATTERN.match(str(col).strip()):
                return col
        return None

    @staticmethod
    def _fy_labels_to_years(series: pd.Series) -> pd.Series:
        """Extract numeric years from fiscal-period labels (e.g. "1976 TQ" -> 1976)."""
        return pd.to_numeric(
            series.astype("string").str.extract(FY_YEAR_PATTERN, expand=False),
            errors="coerce",
        )

    @staticmethod
    def _normalize_fy_column(df: pd.DataFrame, col: str) -> pd.DataFrame:
        """
        Normalize FY column values for plotting and inflation adjustment.

        Process:
        1. Convert an all-year series to datetimes
        2. Keep a series containing a transition quarter as ordered labels
        3. Filter out invalid values (non-numeric, non-TQ strings like "Totals")
        """
        df = df.copy()
        contains_transition_quarter = (
            df[col].astype("string").str.contains("TQ", case=False, na=False).any()
        )

        def norm(x):
            if pd.isna(x):
                return pd.NA
            s = str(x).strip()
            # A transition quarter cannot share a datetime64 column with annual
            # fiscal years without either losing its label or inventing a date.
            # Keep the entire mixed-period axis categorical instead.
            if "TQ" in s.upper():
                match = FY_YEAR_PATTERN.search(s)
                return f"{match.group()} TQ" if match else "1976 TQ"
            # Try to extract a 4-digit year from the value
            # Handle both integer (2020) and float (2020.0) formats
            try:
                year_val = int(float(s))
                if 1900 <= year_val <= 2100:
                    if contains_transition_quarter:
                        return str(year_val)
                    return datetime(year_val, 1, 1)
            except (ValueError, TypeError):
                pass
            return pd.NA

        # Apply normalization first (handles "1976 TQ" and year conversion)
        df[col] = df[col].apply(norm)

        # Filter out rows where normalization resulted in NA
        original_len = len(df)
        df = df.dropna(subset=[col])
        dropped = original_len - len(df)
        if dropped > 0:
            logger.info(f"Dropped {dropped} rows with invalid FY values in '{col}'")

        # Ensure ordinary all-year columns are datetime64[ns] for matplotlib.
        # Mixed annual/TQ columns intentionally remain categorical strings.
        if not contains_transition_quarter and len(df) > 0:
            df[col] = pd.to_datetime(df[col])

        return df

    def _apply_fiscal_year_conversion(
        self,
        df: pd.DataFrame,
        fiscal_year_column: str | bool | None = None,
    ) -> pd.DataFrame:
        """
        Apply FY detection and conversion to DataFrame.

        Args:
            df: Input DataFrame
            fiscal_year_column:
                - None: Auto-detect (default)
                - str: Use this column name
                - False: Disable FY conversion

        Returns:
            DataFrame with FY column converted to datetime
        """
        if fiscal_year_column is False:
            return df

        # Determine which column to convert
        if isinstance(fiscal_year_column, str):
            col = fiscal_year_column
            if col not in df.columns:
                logger.warning(f"fiscal_year_column '{col}' not found in DataFrame")
                return df
        else:
            col = self._detect_fy_column(df)
            if col is None:
                return df

        logger.debug(f"Converting fiscal year column '{col}' to datetime")
        return self._normalize_fy_column(df, col)
