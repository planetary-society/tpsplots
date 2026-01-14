"""Date processing utilities for tpsplots.

Provides shared functions for detecting and processing date columns
in data sources (CSV files, Google Sheets, etc.).
"""

import re

import pandas as pd


def looks_like_date_column(col_name: str, series: pd.Series) -> bool:
    """
    Check if a column contains date-like data.

    Detects columns with values in YYYY-MM-DD format by examining
    the first non-null value in the series.

    Args:
        col_name: Column name (currently unused, reserved for future heuristics)
        series: Pandas Series to check

    Returns:
        bool: True if the column appears to contain dates

    Examples:
        >>> looks_like_date_column("Start Date", pd.Series(["2024-01-15", "2024-06-20"]))
        True
        >>> looks_like_date_column("Name", pd.Series(["Alice", "Bob"]))
        False
    """
    if len(series) == 0:
        return False

    # Get first non-null value
    non_null = series.dropna()
    if len(non_null) == 0:
        return False

    first_val = non_null.iloc[0]

    # Check if value matches date format (YYYY-MM-DD)
    return bool(re.match(r"\d{4}-\d{2}-\d{2}", str(first_val)))


def round_date_to_year(dt_series: pd.Series) -> pd.Series:
    """
    Round dates to nearest year using June 15 cutoff.

    Dates before June 15 round to the current year.
    Dates on or after June 15 round to the next year.

    This provides a sensible mid-year cutoff for visualizations
    that need to display dates as years.

    Args:
        dt_series: Pandas Series of datetime objects

    Returns:
        pd.Series: Series of integer years

    Examples:
        >>> import pandas as pd
        >>> dates = pd.to_datetime(["1959-01-09", "1959-06-15", "1961-12-07"])
        >>> round_date_to_year(dates).tolist()
        [1959, 1960, 1962]

    Rounding rules:
        - 1959-01-09 → 1959 (before June 15)
        - 1959-06-14 → 1959 (before June 15)
        - 1959-06-15 → 1960 (at cutoff, rounds up)
        - 1961-12-07 → 1962 (after June 15)
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
