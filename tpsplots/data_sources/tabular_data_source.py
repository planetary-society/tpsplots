"""
Tabular Data Source Base Class
===============================

Abstract base class for loading and processing tabular data. Provides a
shared data-processing pipeline (column selection, renaming, type casting,
currency cleaning, and fiscal-year conversion) that concrete subclasses
extend by implementing :meth:`_read_raw_df`.

Subclasses
----------
- :class:`GoogleSheetsSource` — loads CSV exports from Google Sheets URLs.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, ClassVar

import pandas as pd

from tpsplots.data_sources.fiscal_year_mixin import FiscalYearMixin
from tpsplots.data_sources.truncate_rows_mixin import TruncateRowsMixin
from tpsplots.processors.dataframe_to_yaml_processor import to_snake_case
from tpsplots.utils.currency_processing import clean_currency_column, looks_like_currency_column

logger = logging.getLogger(__name__)


class TabularDataSource(TruncateRowsMixin, FiscalYearMixin, ABC):
    """
    Abstract base class for tabular data sources.

    Provides a standard pipeline that reads raw data from a subclass-defined
    source and then applies:

    1. Column selection (keep only specified columns)
    2. Column renaming
    3. Type casting overrides
    4. Automatic currency-column cleaning
    5. Fiscal-year column detection and datetime conversion

    Subclasses must implement :meth:`_read_raw_df` to supply the raw
    :class:`~pandas.DataFrame`.

    Configuration can be supplied via constructor arguments **or** via
    class-level attributes (``CAST``, ``COLUMNS``, ``RENAMES``).  Instance
    arguments take precedence.
    """

    # Type mapping for simple type names to pandas dtypes
    TYPE_MAPPING: ClassVar[dict[str, str]] = {
        "int": "int64",
        "float": "float64",
        "str": "object",
        "string": "object",
        "bool": "bool",
        "datetime": "datetime64[ns]",
        "date": "datetime64[ns]",
    }

    # Default for auto-cleaning currency columns (can be overridden in subclass)
    AUTO_CLEAN_CURRENCY: ClassVar[bool] = True

    def __init__(
        self,
        cast: dict[str, str] | None = None,
        columns: list[str] | None = None,
        renames: dict[str, str] | None = None,
        auto_clean_currency: bool | dict | None = None,
        fiscal_year_column: str | bool | None = None,
        truncate_at: bool | str | None = None,
    ) -> None:
        """
        Initialize the TabularDataSource.

        Args:
            cast: Column type overrides (optional, can also be class attribute CAST).
            columns: Columns to keep (optional, can also be class attribute COLUMNS).
            renames: Column renames (optional, can also be class attribute RENAMES).
            auto_clean_currency: Auto-detect and clean currency columns (default True).
                Can be bool or dict with 'enabled' (bool) and 'multiplier' (float) keys.
                When enabled, columns with 80%+ values matching $X,XXX pattern are
                converted to float64 and originals are preserved as {column}_raw.
            fiscal_year_column: Column to convert to datetime (default auto-detect).
                - None: Auto-detect columns named "Fiscal Year", "FY", or "Year"
                - str: Use this specific column name
                - False: Disable fiscal year conversion
            truncate_at: Truncate rows at the first matching first-column value.
                - None: Use the source default marker
                - True: Force use of the source default marker
                - False: Disable truncation
                - str: Use this exact trimmed marker
        """
        self._cast = cast
        self._columns = columns
        self._renames = renames
        self._auto_clean_currency = auto_clean_currency
        self._fiscal_year_column = fiscal_year_column
        self._truncate_at = truncate_at

    # ------------------------------------------------------------------
    # Abstract method — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def _read_raw_df(self) -> pd.DataFrame:
        """
        Read and return the raw DataFrame from the underlying data source.

        Subclasses must override this to provide the unprocessed data.

        Returns:
            A raw :class:`~pandas.DataFrame`.
        """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def data(self) -> pd.DataFrame:
        """
        Return the processed DataFrame.

        Returns:
            A deep copy of the processed pandas DataFrame.
        """
        return self._df.copy(deep=True)

    def columns(self) -> list[str]:
        """
        Return list of column names in the processed DataFrame.

        Returns:
            List of column names.
        """
        return list(self._df.columns)

    def __getattr__(self, name: str) -> list[Any]:
        """
        Provide attribute-style access to DataFrame columns.

        Args:
            name: The attribute name to access.

        Returns:
            List of values from the corresponding column.

        Raises:
            AttributeError: If the name doesn't match any column.
        """
        # Convert attribute name to match potential column names
        # (e.g., 'award_date' could match 'Award Date')
        normalized_name = name.replace("_", " ").title()

        # Try exact match first
        if name in self._df.columns:
            return self._df[name].tolist()

        # Try normalized version
        if normalized_name in self._df.columns:
            return self._df[normalized_name].tolist()

        # Try case-insensitive match
        for col in self._df.columns:
            if col.lower() == name.lower():
                return self._df[col].tolist()

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    # ------------------------------------------------------------------
    # Cached data pipeline
    # ------------------------------------------------------------------

    @cached_property
    def _df(self) -> pd.DataFrame:
        """
        Load and process the data into a DataFrame.

        This property is computed once and cached.  It orchestrates:

        1. Reading raw data via :meth:`_read_raw_df`
        2. Column selection (if columns defined)
        3. Column renaming (if renames defined)
        4. Type casting overrides (if cast defined)
        5. Automatic currency-column cleaning
        6. Fiscal-year column conversion

        Returns:
            The processed pandas DataFrame.
        """
        # Read the raw data from the subclass
        df = self._read_raw_df()
        df = self._truncate_rows(df)

        # Select columns if specified (instance attribute takes precedence)
        columns = self._columns or getattr(self.__class__, "COLUMNS", None)
        if columns:
            missing = [col for col in columns if col not in df.columns]
            if missing:
                logger.warning(f"Columns not found in data: {missing}")
            existing = [col for col in columns if col in df.columns]
            df = df[existing]

        # Rename columns if specified (instance attribute takes precedence)
        renames = self._renames or getattr(self.__class__, "RENAMES", None)
        if renames:
            df = df.rename(columns=renames)

        # Apply type casting overrides
        df = self._cast_columns(df)

        # Auto-clean currency columns if enabled
        df = self._auto_clean_currency_columns(df)

        # Apply fiscal year conversion (auto-detects or uses configured column)
        df = self._apply_fiscal_year_conversion(df, self._fiscal_year_column)
        df = self._annotate_value_columns_metadata(df)

        return df

    def _resolve_truncate_markers(self) -> tuple[str, ...]:
        """Resolve truncation markers, supporting constructor-level override."""
        truncate_at = self._truncate_at
        if truncate_at is False:
            return ()

        default = getattr(self.__class__, "TRUNCATE_AT", None)
        candidate = default if truncate_at in (None, True) else truncate_at

        if candidate is None or candidate is False:
            return ()

        if isinstance(candidate, str):
            normalized = candidate.strip()
            return (normalized,) if normalized else ()

        if isinstance(candidate, (list, tuple)):
            markers = tuple(str(item).strip() for item in candidate if str(item).strip())
            return markers

        return ()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cast_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply type casting overrides from cast configuration.

        This method only applies casting for columns explicitly defined in cast,
        leaving other columns with their pandas-inferred types.

        For numeric types (int, float), uses pd.to_numeric with errors='coerce'
        to convert invalid values to NaN, then drops rows with NaN in those columns.
        This is useful for filtering out summary rows like "Totals" from data.

        Args:
            df: The input DataFrame.

        Returns:
            DataFrame with type overrides applied.
        """
        # Get cast dictionary (instance attribute takes precedence)
        cast_dict = self._cast or getattr(self.__class__, "CAST", None)
        if not cast_dict:
            return df

        df = df.copy()
        columns_to_dropna = []

        for col, dtype in cast_dict.items():
            if col not in df.columns:
                logger.warning(f"CAST column '{col}' not found in DataFrame")
                continue

            # Normalize simple type names to pandas dtypes
            normalized_dtype = self.TYPE_MAPPING.get(dtype, dtype)

            try:
                # Special handling for datetime
                if "datetime" in str(normalized_dtype):
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    columns_to_dropna.append(col)
                # Special handling for numeric types - use to_numeric for proper coercion
                elif normalized_dtype in ("int64", "float64") or dtype in ("int", "float"):
                    df[col] = pd.to_numeric(
                        self._normalize_numeric_strings(df[col]),
                        errors="coerce",
                    )
                    columns_to_dropna.append(col)
                    # Int conversion deferred until after dropna (see loop below)
                else:
                    df[col] = df[col].astype(normalized_dtype, errors="ignore")
                logger.debug(f"Cast column '{col}' to {normalized_dtype}")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to cast column '{col}' to {normalized_dtype}: {e}")

        # Drop rows with NaN values in coerced columns (filters out invalid rows like "Totals")
        if columns_to_dropna:
            original_len = len(df)
            df = df.dropna(subset=columns_to_dropna)
            dropped = original_len - len(df)
            if dropped > 0:
                logger.info(
                    f"Dropped {dropped} rows with invalid values in columns: {columns_to_dropna}"
                )

        # Now convert float columns to int where requested
        for col, dtype in cast_dict.items():
            is_int_type = dtype in ("int", "int64") or self.TYPE_MAPPING.get(dtype) == "int64"
            if col in df.columns and is_int_type and df[col].notna().all():
                df[col] = df[col].astype("int64")

        return df

    def _normalize_numeric_strings(self, series: pd.Series) -> pd.Series:
        """Strip thousands separators from string-like values before numeric coercion."""
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            return series.astype(str).str.replace(",", "", regex=False)
        return series

    def _annotate_value_columns_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Record auto-detected numeric value columns for downstream metadata generation."""
        value_columns: dict[str, str] = {}
        fiscal_year_col = self._resolve_metadata_fiscal_year_column(df)

        for col in df.select_dtypes(include="number").columns:
            if col == fiscal_year_col or col.endswith("_raw"):
                continue

            key = to_snake_case(col)
            if key in value_columns and value_columns[key] != col:
                logger.warning(
                    "Skipping metadata alias '%s' for column '%s'; already assigned to '%s'",
                    key,
                    col,
                    value_columns[key],
                )
                continue
            value_columns[key] = col

        if value_columns:
            df.attrs["value_columns"] = value_columns
        else:
            df.attrs.pop("value_columns", None)

        return df

    def _resolve_metadata_fiscal_year_column(self, df: pd.DataFrame) -> str | None:
        """Resolve the fiscal-year column name used for auto-generated metadata."""
        if self._fiscal_year_column is False:
            return None
        if isinstance(self._fiscal_year_column, str):
            return self._fiscal_year_column if self._fiscal_year_column in df.columns else None
        return FiscalYearMixin._detect_fy_column(df)

    def _auto_clean_currency_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Auto-detect and clean currency columns.

        Scans object-type columns for currency patterns ($X,XXX or $X,XXX.XX).
        When 80%+ of non-null values match, the column is converted to float64
        and the original values are preserved in a {column}_raw column.

        This behavior is controlled by:
        - Instance parameter: auto_clean_currency (takes precedence)
        - Class attribute: AUTO_CLEAN_CURRENCY (default True)

        The auto_clean_currency parameter can be:
        - bool: True to enable with multiplier=1.0, False to disable
        - dict: {'enabled': bool, 'multiplier': float} for custom multiplier

        Args:
            df: The input DataFrame.

        Returns:
            DataFrame with currency columns cleaned and originals preserved.
        """
        # Determine if auto-cleaning is enabled and extract multiplier
        auto_clean = self._auto_clean_currency
        multiplier = 1.0

        if auto_clean is None:
            auto_clean = getattr(self.__class__, "AUTO_CLEAN_CURRENCY", True)

        # Handle dict or Pydantic model config with enabled/multiplier
        if hasattr(auto_clean, "enabled"):
            # Pydantic model (CurrencyCleaningConfig)
            multiplier = getattr(auto_clean, "multiplier", 1.0)
            auto_clean = getattr(auto_clean, "enabled", True)
        elif isinstance(auto_clean, dict):
            # Raw dict from YAML
            multiplier = auto_clean.get("multiplier", 1.0)
            auto_clean = auto_clean.get("enabled", True)

        if not auto_clean:
            return df

        df = df.copy()

        for col in df.select_dtypes("object").columns:
            if looks_like_currency_column(col, df[col]):
                # Preserve original values
                df[f"{col}_raw"] = df[col]
                # Clean the column with optional multiplier
                df[col] = clean_currency_column(df[col], multiplier=multiplier)
                logger.debug(f"Auto-cleaned currency column '{col}' with multiplier {multiplier}")

        return df
