"""Mixin for fiscal year detection and datetime conversion."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Pattern matches: "Fiscal Year", "FY", "FY2024", "Year" (case-insensitive)
FY_COLUMN_PATTERN = re.compile(r"^(fiscal\s*year|fy\d{0,4}|year)$", re.IGNORECASE)

# Year embedded in a fiscal-period label, e.g. "1976 TQ" or "FY2024"
FY_YEAR_PATTERN = re.compile(r"(\d{4})")

# Anchored transition-quarter label: "TQ", "1976TQ", "1976 TQ", "FY1976 TQ",
# "FY76 TQ" (with optional surrounding whitespace). Anchored so a stray "tq"
# substring (e.g. "not-tq-related", "Totals-TQE") never flips the whole column.
TQ_LABEL_PATTERN = re.compile(r"^\s*(?:FY)?\s*\d{0,4}\s*TQ\s*$", re.IGNORECASE)

# Plausible calendar-year bounds and the minimum fraction of a candidate
# column's non-null values that must parse as such before it is treated as a
# fiscal-year column. A column named "Year" whose values are mostly IDs,
# fractions, or free text (fewer than this fraction plausible) is left alone
# rather than silently coerced to datetime (or emptied) two steps upstream of
# a cryptic render error.
MIN_YEAR = 1900
MAX_YEAR = 2100
FY_PLAUSIBILITY_THRESHOLD = 0.8


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
    def _tq_mask(series: pd.Series) -> pd.Series:
        """Boolean mask of transition-quarter labels (e.g. "1976 TQ")."""
        return series.astype("string").str.contains(TQ_LABEL_PATTERN, na=False)

    @staticmethod
    def _fy_years(series: pd.Series) -> pd.Series:
        """
        Numeric year for each fiscal-period value.

        Handles datetime64 columns as well as integer and transition-quarter
        label columns (e.g. "1976", "1976 TQ"). Unparseable values become NaN
        (never pd.NA), so comparisons yield plain boolean masks.
        """
        if pd.api.types.is_datetime64_any_dtype(series):
            return series.dt.year
        return FiscalYearMixin._fy_labels_to_years(series).astype("float64")

    @staticmethod
    def _fy_year_mask(series: pd.Series, year: int) -> pd.Series:
        """
        Boolean mask of fiscal periods that fall in ``year``.

        Note: an annual row and a transition-quarter row of the same year
        (e.g. "1976" and "1976 TQ") both match.
        """
        return FiscalYearMixin._fy_years(series).eq(year)

    @staticmethod
    def _fy_cell(df: pd.DataFrame, year: int, col: str = "Fiscal Year") -> datetime | str:
        """
        New fiscal-year cell value matching the column's dtype.

        Datetime columns get ``datetime(year, 1, 1)``; transition-quarter
        label columns stay categorical and get ``str(year)``.
        """
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return datetime(year, 1, 1)
        return str(year)

    @staticmethod
    def _sort_by_fiscal_year(df: pd.DataFrame, col: str = "Fiscal Year") -> pd.DataFrame:
        """Sort by fiscal year, keeping a transition quarter after its year."""
        series = df[col]
        if pd.api.types.is_datetime64_any_dtype(series):
            return df.sort_values(col).reset_index(drop=True)
        years = FiscalYearMixin._fy_years(series).to_numpy(dtype=float)
        is_tq = FiscalYearMixin._tq_mask(series).to_numpy(dtype=bool)
        return df.iloc[np.lexsort((is_tq, years))].reset_index(drop=True)

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
        contains_transition_quarter = FiscalYearMixin._tq_mask(df[col]).any()

        def norm(x):
            if pd.isna(x):
                return pd.NA
            s = str(x).strip()
            # A transition quarter cannot share a datetime64 column with annual
            # fiscal years without either losing its label or inventing a date.
            # Keep the entire mixed-period axis categorical instead.
            if TQ_LABEL_PATTERN.match(s):
                match = FY_YEAR_PATTERN.search(s)
                return f"{match.group()} TQ" if match else "1976 TQ"
            # Try to extract a 4-digit year from the value
            # Handle both integer (2020) and float (2020.0) formats
            try:
                year_val = int(float(s))
                if MIN_YEAR <= year_val <= MAX_YEAR:
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

    @staticmethod
    def _year_parse_fraction(series: pd.Series) -> float:
        """
        Fraction of non-null values that parse as plausible calendar years.

        A value counts as a plausible year when it is a transition-quarter
        label (e.g. "1976 TQ") or coerces to a number in ``[MIN_YEAR, MAX_YEAR]``
        (int, float, and string forms all handled). Returns ``1.0`` when the
        column has no non-null values so an all-empty column is not spuriously
        rejected.

        Every value is coerced to string before any regex/numeric parsing, so a
        float-typed or object-with-floats column can never raise a
        ``str``-accessor / regex type error here.
        """
        non_null = series.dropna()
        total = len(non_null)
        if total == 0:
            return 1.0

        # Transition-quarter labels are legitimately convertible.
        tq = FiscalYearMixin._tq_mask(non_null).to_numpy(dtype=bool)
        # Numeric years in any form ("2020", 2020, 2020.0, "1958.0").
        numeric = pd.to_numeric(non_null.astype("string").str.strip(), errors="coerce")
        in_range = numeric.between(MIN_YEAR, MAX_YEAR).fillna(False).to_numpy(dtype=bool)

        return float((tq | in_range).sum()) / total

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

        # Plausibility gate: only convert when most values actually look like
        # calendar years. This both prevents a mislabeled column (IDs, fractions,
        # free text under a "Year" header) from being silently emptied/coerced,
        # and guarantees the str/regex parsing below never sees an unexpected
        # dtype it cannot handle.
        fraction = self._year_parse_fraction(df[col])
        if fraction < FY_PLAUSIBILITY_THRESHOLD:
            logger.warning(
                "Skipping fiscal-year conversion for column '%s': only %.0f%% of "
                "its non-null values parse as plausible years (%d-%d). Set "
                "fiscal_year_column to choose a different column or false to disable.",
                col,
                fraction * 100,
                MIN_YEAR,
                MAX_YEAR,
            )
            return df

        logger.debug(f"Converting fiscal year column '{col}' to datetime")
        return self._normalize_fy_column(df, col)
