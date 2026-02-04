"""DataFrame transformation utilities for tpsplots.

Provides shared functions for column transformations used by data controllers
(CSVController, GoogleSheetsController, etc.).
"""

import logging

import pandas as pd

from tpsplots.exceptions import DataSourceError

logger = logging.getLogger(__name__)

# Valid cast types for column type conversion
VALID_CAST_TYPES = {"int", "float", "str", "datetime"}


def apply_column_cast(
    df: pd.DataFrame,
    cast: dict[str, str] | None,
    warn_unknown: bool = True,
) -> pd.DataFrame:
    """Apply type casting to DataFrame columns.

    Converts columns to specified types with proper error handling.
    Unknown types are logged as warnings and skipped.

    Args:
        df: DataFrame to transform (modified in place and returned)
        cast: Dict mapping column names to type strings.
              Valid types: "int", "float", "str", "datetime"
        warn_unknown: If True, log warning for unknown cast types

    Returns:
        The transformed DataFrame

    Examples:
        >>> df = pd.DataFrame({"year": ["2020", "2021"], "amount": ["100", "200"]})
        >>> apply_column_cast(df, {"year": "int", "amount": "float"})
           year  amount
        0  2020   100.0
        1  2021   200.0
    """
    if not cast:
        return df

    for col, dtype in cast.items():
        if col not in df.columns:
            continue

        if dtype not in VALID_CAST_TYPES:
            if warn_unknown:
                logger.warning(
                    f"Unknown cast type '{dtype}' for column '{col}', "
                    f"valid types: {VALID_CAST_TYPES}"
                )
            continue

        if dtype == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif dtype == "float":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif dtype == "str":
            df[col] = df[col].astype(str)
        elif dtype == "datetime":
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def apply_column_renames(
    df: pd.DataFrame,
    renames: dict[str, str] | None,
) -> pd.DataFrame:
    """Rename columns in a DataFrame.

    Args:
        df: DataFrame to transform
        renames: Dict mapping old column names to new names

    Returns:
        DataFrame with renamed columns
    """
    if not renames:
        return df
    return df.rename(columns=renames)


def filter_columns(
    df: pd.DataFrame,
    columns: list[str] | None,
    source_name: str = "data source",
) -> pd.DataFrame:
    """Filter DataFrame to specified columns.

    Args:
        df: DataFrame to filter
        columns: List of column names to keep. If None, returns df unchanged.
        source_name: Name of data source for error messages

    Returns:
        DataFrame with only the specified columns

    Raises:
        DataSourceError: If any specified columns are not found
    """
    if not columns:
        return df

    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataSourceError(
            f"Columns not found in {source_name}: {missing}. Available columns: {list(df.columns)}"
        )
    return df[columns]
