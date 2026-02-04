"""Currency processing utilities for tpsplots.

Provides shared functions for detecting and cleaning currency columns
in data sources (Google Sheets, NASA budget data, etc.).

This module extracts the currency cleaning logic originally from
NASABudget._clean_currency_column() so it can be reused by multiple
data sources.
"""

import re

import pandas as pd

# Regex to find and remove currency symbols, commas, and 'M' or 'B' suffixes
# Extracted from NASABudget._CURRENCY_RE - handles $, commas, and M/B suffixes
CURRENCY_RE = re.compile(r"[\$,]|\s*[MB]$", flags=re.IGNORECASE)

# Stricter pattern for auto-detection (must start with $)
# Handles formats like $42,013 and $1,234.56
CURRENCY_DETECT_PATTERN = re.compile(r"^\$[\d,]+(?:\.\d{1,2})?$")


def looks_like_currency_column(
    col_name: str,
    series: pd.Series,
    threshold: float = 0.8,
    min_samples: int = 3,
) -> bool:
    """
    Check if a column contains currency-formatted data.

    Detects columns with values in $X,XXX or $X,XXX.XX format by examining
    non-null values in the series. Returns True if at least `threshold`
    proportion of non-null values match the currency pattern.

    Args:
        col_name: Column name (currently unused, reserved for future heuristics)
        series: Pandas Series to check
        threshold: Minimum proportion of values that must match (default 0.8)
        min_samples: Minimum number of non-null values required (default 3)

    Returns:
        bool: True if the column appears to contain currency values

    Examples:
        >>> looks_like_currency_column("Amount", pd.Series(["$42,013", "$1,234.56"]))
        True
        >>> looks_like_currency_column("Name", pd.Series(["Alice", "Bob"]))
        False
        >>> looks_like_currency_column("Mixed", pd.Series(["$100", "N/A", "$200"]))
        True  # 2/3 match, above 66% but below 80%... returns False with default threshold
    """
    non_null = series.dropna().astype(str)

    if len(non_null) < min_samples:
        return False

    matches = non_null.str.match(CURRENCY_DETECT_PATTERN).sum()
    return (matches / len(non_null)) >= threshold


def clean_currency_column(series: pd.Series, multiplier: float = 1.0) -> pd.Series:
    """
    Clean currency column by removing symbols and converting to numeric.

    Removes dollar signs ($), commas, and M/B suffixes, then converts
    to float64 and optionally multiplies by a scale factor.

    This function was extracted from NASABudget._clean_currency_column()
    to enable reuse across data sources.

    Args:
        series: A pandas Series containing currency values (e.g., "$42,013", "$1.5M")
        multiplier: Scale factor to apply after cleaning (default 1.0).
                   Use 1_000_000 for NASA budget data that's in millions.

    Returns:
        A Series of float64 values, optionally multiplied by the multiplier

    Examples:
        >>> clean_currency_column(pd.Series(["$42,013", "$1,234.56"]))
        0    42013.0
        1     1234.56
        dtype: float64

        >>> clean_currency_column(pd.Series(["$1.5"]), multiplier=1_000_000)
        0    1500000.0
        dtype: float64
    """
    return (
        series.astype(str)
        .str.replace(CURRENCY_RE, "", regex=True)
        .apply(pd.to_numeric, errors="coerce")
        .mul(multiplier)
        .astype("float64")
    )
