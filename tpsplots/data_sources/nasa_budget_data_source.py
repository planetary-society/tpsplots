"""
NASA Budget Data Source Documentation
=====================================

This module provides classes for handling NASA budget data from various sources.
It supports both string and datetime fiscal year representations.

Note: Inflation adjustment is NOT automatic. Use InflationAdjustmentProcessor
explicitly in controllers to apply inflation adjustments to monetary columns.

Key Classes
----------
- NASABudget: Base class for handling NASA budget data
- Historical: Concrete class for historical NASA budget data
- Directorates: Concrete class for NASA directorate budget data
- Science: Concrete class for NASA Science Mission Directorate budget data

Usage Example
------------
```python
from tpsplots.data_sources.nasa_budget_data_source import Historical
from tpsplots.processors import InflationAdjustmentConfig, InflationAdjustmentProcessor

# Create a data source instance
budget = Historical()

# Get the cleaned DataFrame (raw nominal values)
df = budget.data()

# Access values via attribute-style getters
fy = budget.fiscal_year  # Returns list of fiscal years
requests = budget.pbr  # Returns list of presidential budget requests

# For inflation-adjusted values, use InflationAdjustmentProcessor:
config = InflationAdjustmentConfig(nnsi_columns=["PBR", "Appropriation"])
df = InflationAdjustmentProcessor(config).process(df)
# Now df has PBR_adjusted_nnsi and Appropriation_adjusted_nnsi columns
```

Working with Fiscal Years
------------------------
The module handles fiscal years in both string and datetime formats:

- When loading data from CSV sources, the fiscal year column is automatically
  converted to datetime objects for easier plotting and manipulation.

- Special cases like the "1976 TQ" (Transition Quarter) are preserved as strings.

- When converting fiscal years to strings for display, use standard string
  formatting: `f"{fiscal_year:%Y}"` for a four-digit year representation.
"""

from __future__ import annotations

import io

# Assumed external library for inflation adjustments
import logging
import re
import ssl
from collections.abc import Callable
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar
from urllib.error import URLError

import certifi
import pandas as pd
import requests

from tpsplots.data_sources.fiscal_year_mixin import FiscalYearMixin
from tpsplots.utils.currency_processing import clean_currency_column

logger = logging.getLogger(__name__)


# ─────────────────────────── base class ────────────────────────────
class NASABudget(FiscalYearMixin):
    """
    Base class for loading, cleaning, and accessing NASA budget data.

    This class provides the core logic for reading CSV data, cleaning it,
    adding inflation-adjusted columns, and creating dynamic attributes
    for accessing monetary data.

    Subclasses should define:
    - CSV_URL (str): The URL of the CSV data source.
    - COLUMNS (List[str], optional): A list of columns to keep.
    - RENAMES (Dict[str, str], optional): A dictionary for renaming columns.
    - MONETARY_COLUMNS (List[str], optional): A list of columns containing
      monetary values that should have adjusted versions created.
    - PERCENTAGE_COLUMNS (List[str], optional): A list of percent-like columns
      containing values such as "0.7%" that should be normalized to floats.
    """

    # ── core API ────────────────────────────────────────────────────
    def __init__(self, csv_source: str | Path) -> None:
        """
        Initializes the NASABudget instance.

        The data loading and processing pipeline is triggered lazily when
        the `_df` cached property is first accessed.

        Args:
            csv_source: The path to a local CSV file or a URL of a CSV file.
        """
        self._csv_source = str(csv_source)

    def data(self) -> pd.DataFrame:
        """
        Return the fully cleaned & augmented DataFrame.

        Returns:
            A deep copy of the internal pandas DataFrame containing the
            processed NASA budget data.
        """
        return self._df.copy(deep=True)

    def columns(self) -> list[str]:
        """
        Return a list of column names in the processed DataFrame.

        Returns:
            A list of strings representing the column names.
        """
        return list(self._df.columns)

    def __getattr__(self, name: str) -> list[Any]:
        """
        Provides attribute-style access to DataFrame columns.

        If the requested attribute name matches a column name in the internal
        DataFrame, its values are returned as a list. Otherwise, raises an
        AttributeError.

        This method is called only if the attribute is not found in the
        standard way (i.e., not in the instance's __dict__ or class's __dict__).

        Args:
            name: The name of the attribute being accessed.

        Returns:
            A list containing the values from the corresponding DataFrame column.

        Raises:
            AttributeError: If the name does not match any DataFrame column.
        """
        if name in self._df.columns:
            # Return the column data as a list
            return self._df[name].tolist()
        # If the name is not a column, raise the standard AttributeError
        raise AttributeError(name)

    # ── auto getters for monetary columns ──────────────────────────
    def __init_subclass__(cls, **kw):
        """
        Automatically creates attribute getters for monetary columns in subclasses.

        This class method is called automatically when a class inherits from
        NASABudget. It iterates through the `MONETARY_COLUMNS` defined in the
        subclass and dynamically creates a raw attribute (e.g., `appropriation`)
        returning the nominal list.

        Note: Inflation-adjusted values are no longer automatically generated.
        Use InflationAdjustmentProcessor explicitly in controllers to apply
        inflation adjustments.

        Args:
            cls: The subclass being initialized.
            **kw: Arbitrary keyword arguments.
        """
        super().__init_subclass__(**kw)
        # Iterate through columns listed in the subclass's MONETARY_COLUMNS
        for col in getattr(cls, "MONETARY_COLUMNS", []):
            # Create a 'pythonic' attribute name (lowercase, underscores)
            attr = re.sub(r"\W+", "_", col).lower()
            # If the raw attribute doesn't exist on the class, create it
            if attr not in cls.__dict__:
                setattr(cls, attr, cls._mk_raw(col))

    @classmethod
    def _mk_raw(cls, col: str) -> Callable[[NASABudget], list[float]]:
        """
        Creates a getter function for a raw monetary column.

        This function returns a callable that, when called on a NASABudget
        instance, will return the specified column's data as a list of floats.

        Args:
            col: The name of the column in the DataFrame.

        Returns:
            A callable that takes a NASABudget instance and returns a list of floats.
        """
        # Lambda function that accesses the specified column from the instance's
        # DataFrame and converts it to a list.
        return lambda self: self._df[col].tolist()

    # ── DataFrame construction pipeline ────────────────────────────
    @cached_property
    def _df(self) -> pd.DataFrame:
        """
        Loads, cleans, and processes the NASA budget data into a DataFrame.

        This property is computed only once per instance and the result is cached.
        It orchestrates the data loading, subsetting, renaming, cleaning, and
        adjustment steps.

        Returns:
            The fully processed pandas DataFrame.
        """
        # Read the raw data from the source (file or URL)
        raw = self._read_csv()

        # Subset columns if COLUMNS is defined in the subclass
        if subset := getattr(self.__class__, "COLUMNS", None):
            raw = raw[subset]

        # Rename columns if RENAMES is defined in the subclass
        if ren := getattr(self.__class__, "RENAMES", None):
            raw = raw.rename(columns=ren)

        # Apply general cleaning rules (currency, dates, fiscal years)
        return self._clean(raw)

    # ── I/O helpers ────────────────────────────────────────────────
    @staticmethod
    def _fetch_url_content(url: str) -> str:
        """
        Fetch content from a URL.

        Args:
            url: The URL to fetch

        Returns:
            The text content of the response
        """
        try:
            # Try direct read first
            return pd.read_csv(url).to_csv(index=False)
        except (URLError, ssl.SSLError):
            # If direct read fails, use requests
            response = requests.get(url, timeout=30, verify=certifi.where())
            response.raise_for_status()
            return response.text

    def _read_csv(self) -> pd.DataFrame:
        """
        Reads the CSV data from the source.

        Returns:
            A pandas DataFrame containing the raw data from the CSV source.

        Raises:
            URLError, ssl.SSLError, requests.exceptions.RequestException:
                If the data cannot be fetched from the URL.
            FileNotFoundError: If the local file does not exist.
        """
        logger.debug(f"Reading from source: {self._csv_source}")  # Added for visibility

        # Check if it's a URL or local file
        if self._csv_source.startswith(("http://", "https://")):
            text = self._fetch_url_content(self._csv_source)
            df = pd.read_csv(io.StringIO(text))
        else:
            # Local file - read directly
            df = pd.read_csv(self._csv_source)

        return df

    # ── cleaning helpers ───────────────────────────────────────────
    def _clean_currency_column(self, series: pd.Series) -> pd.Series:
        """Clean currency column by converting from millions to dollars.

        Uses the shared clean_currency_column utility with a multiplier
        of 1,000,000 to convert NASA budget values from millions to dollars.

        Args:
            series: A pandas Series containing currency values in millions

        Returns:
            A Series of float64 values multiplied by 1,000,000 (converted to dollars)
        """
        return clean_currency_column(series, multiplier=1_000_000)

    def _clean_percentage_column(self, series: pd.Series) -> pd.Series:
        """Clean percentage-like column values into numeric percent points.

        Handles values such as "0.72%", "0.72", 0.72, and "1,200%".
        Invalid placeholders (e.g., "", "n/a", "--") are coerced to NaN.
        """
        cleaned = (
            series.astype("string")
            .str.strip()
            .replace(
                {
                    "": pd.NA,
                    "nan": pd.NA,
                    "None": pd.NA,
                    "N/A": pd.NA,
                    "n/a": pd.NA,
                    "--": pd.NA,
                },
                regex=False,
            )
            .str.replace("%", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        return pd.to_numeric(cleaned, errors="coerce")

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies general cleaning rules to the DataFrame.

        Cleans columns identified as currency-like, date-style, or fiscal year
        columns. Handles the special "1976 TQ" case for fiscal years. Ensures
        fiscal year columns remain as strings.

        Args:
            df: The input pandas DataFrame to clean.

        Returns:
            A new DataFrame with cleaned data.
        """
        df = df.copy()  # Work on a copy to avoid modifying the original DataFrame

        # Get MONETARY_COLUMNS directly from the class to avoid triggering __getattr__
        monetary_columns = getattr(self.__class__, "MONETARY_COLUMNS", [])
        percentage_columns = getattr(self.__class__, "PERCENTAGE_COLUMNS", [])

        # Clean currency-like columns: properly handle M/B suffixes with correct multipliers
        for col in df.select_dtypes("object"):
            # Check if the column contains '$' characters (indicating currency)
            # OR if the column is listed in MONETARY_COLUMNS
            if (
                df[col].astype(str).str.contains(r"\$", na=False).any()
                or col in monetary_columns  # Use the class attribute directly
            ):
                df[col] = self._clean_currency_column(df[col])

        # Clean known percentage columns.
        for col in percentage_columns:
            if col in df.columns:
                df[col] = self._clean_percentage_column(df[col])

        # Clean date-style columns: convert to datetime objects.
        # Identifies columns ending with 'date', 'signed', or 'updated' (case-insensitive).
        for col in df.columns:
            if re.search(r"(date|signed|updated)$", str(col), flags=re.I):
                # Convert to datetime, coercing errors to NaT (Not a Time)
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

        # Use mixin for fiscal year column conversion (replaces inline norm() function)
        df = self._apply_fiscal_year_conversion(df)

        return df

    # ── misc helpers ───────────────────────────────────────────────
    @staticmethod
    def _detect_fy(df: pd.DataFrame) -> str:
        """
        Detects the fiscal year column name in a DataFrame.

        Searches for columns matching patterns like 'FY####' or names like
        'fiscal year', 'fy', or 'year' (case-insensitive).

        Args:
            df: The pandas DataFrame to inspect.

        Returns:
            The name of the detected fiscal year column.

        Raises:
            ValueError: If no fiscal year column is detected.
        """
        for c in df.columns:
            if re.fullmatch(r"FY\d{2,4}", str(c), flags=re.I) or str(c).lower() in {
                "fiscal year",
                "fy",
                "year",
            }:
                return c
        logger.warning("No fiscal-year column detected.")
        return None

    def _fy_col(self) -> str:
        """
        Returns the detected fiscal year column name for this instance.

        The detection is performed only on the first call and the result is
        cached per instance.

        Returns:
            The name of the fiscal year column.
        """
        # Check if the fiscal year column name is already cached in the instance's dictionary
        if "_fy_name" not in self.__dict__:
            # If not cached, detect it from the processed DataFrame (_df)
            self.__dict__["_fy_name"] = self._detect_fy(self._df)
        # Return the cached name
        return self.__dict__["_fy_name"]

    @staticmethod
    def _current_fy() -> int:
        """
        Calculates the current fiscal year based on the current date.

        The fiscal year starts in October.

        Returns:
            The current fiscal year as an integer.
        """
        today = date.today()
        # If the current month is October or later (>= 10), the FY is the next calendar year.
        # Otherwise, it's the current calendar year.
        return today.year + (today.month >= 10)

    @staticmethod
    def _prior_fy() -> int:
        """
        Calculates the prior fiscal year based on the current date.

        This is typically the target year for inflation adjustments.

        Returns:
            The prior fiscal year as an integer.
        """
        # Calculate the date one year ago
        last_year_date = date.today() - pd.DateOffset(years=1)
        # Determine the fiscal year for that date
        return last_year_date.year + (last_year_date.month >= 10)


# ────────────────────────── concrete sheets ─────────────────────────
class Historical(NASABudget):
    """
    Represents historical NASA budget data.

    Loads data from a specific Google Sheets CSV URL and defines the columns
    to keep, how to rename them, and which ones are monetary for adjustment.
    """

    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=670209929"
    )
    # Define the specific columns to load from the source CSV
    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Presidential Administration",
        "White House Budget Release Date",
        "White House Budget Submission",
        "Appropriation",
        "Outlays",
        "% of U.S. Spending",
        "% of U.S. Discretionary Spending",
    ]
    # Define how to rename columns after loading
    RENAMES: ClassVar[dict[str, str]] = {"White House Budget Submission": "PBR"}
    # Define which columns contain monetary values that need inflation adjustment
    MONETARY_COLUMNS: ClassVar[list[str]] = ["PBR", "Appropriation", "Outlays"]
    PERCENTAGE_COLUMNS: ClassVar[list[str]] = [
        "% of U.S. Spending",
        "% of U.S. Discretionary Spending",
    ]

    def __init__(self) -> None:
        """Initializes the Historical budget data instance."""
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL)


class ScienceDivisions(NASABudget):
    """
    Represents NASA Science Directorate budget data.

    Loads data from a specific Google Sheets CSV URL. COLUMNS, RENAMES, and
    MONETARY_COLUMNS are placeholders and should be defined based on the
    actual structure of the Science sheet.
    """

    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=36975677"
    )
    # define COLUMNS / RENAMES / MONETARY_COLUMNS when ready
    # Example placeholders:
    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Astrophysics",
        "Planetary Science",
        "Earth Science",
        "Heliophysics",
    ]
    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Astrophysics",
        "Planetary Science",
        "Earth Science",
        "Heliophysics",
    ]

    def __init__(self) -> None:
        """Initializes the Science budget data instance."""
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL)


class Directorates(NASABudget):
    """
    Represents NASA Directorate budget data.

    Loads data from a specific Google Sheets CSV URL. COLUMNS, RENAMES, and
    MONETARY_COLUMNS are placeholders and should be defined based on the
    actual structure of the Directorates sheet.
    """

    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=1870113890"
    )
    # define COLUMNS / RENAMES / MONETARY_COLUMNS when ready
    # Example placeholders:
    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Aeronautics",
        "Exploration",
        "Space Operations",
        "STMD",
        "SMD",
        "Education/STEM Outreach",
        "Cross Agency Support/CECR",
    ]
    RENAMES: ClassVar[dict[str, str]] = {
        "Cross Agency Support/CECR": "Facilities, IT, & Salaries",
        "Education/STEM Outreach": "STEM Education",
        "STMD": "Space Technology",
        "Exploration": "Deep Space Exploration Systems",
        "SMD": "Science",
    }
    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Aeronautics",
        "Space Technology",
        "Deep Space Exploration Systems",
        "Space Operations",
        "Science",
        "STEM Education",
        "Facilities, IT, & Salaries",
    ]

    def __init__(self) -> None:
        """Initializes the Directorates budget data instance."""
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL)


class Science(NASABudget):
    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/"
        "export?format=csv&gid=1298630212"
    )

    COLUMNS: ClassVar[list[str]] = ["Fiscal Year", "NASA Science (millions of $)"]
    RENAMES: ClassVar[dict[str, str]] = {"NASA Science (millions of $)": "NASA Science"}
    MONETARY_COLUMNS: ClassVar[list[str]] = ["NASA Science"]

    def __init__(self) -> None:
        super().__init__(self.CSV_URL)


class Workforce(NASABudget):
    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/"
        "export?format=csv&gid=479410406"
    )

    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Full-time Permanent (FTP)",
        "Full-time Equivalent (FTE)",
    ]

    # Columns that need comma removal and numeric conversion
    NUMERIC_COLUMNS: ClassVar[list[str]] = [
        "Full-time Permanent (FTP)",
        "Full-time Equivalent (FTE)",
    ]

    def __init__(self) -> None:
        super().__init__(self.CSV_URL)

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Override to clean comma-separated numeric columns."""
        # Apply standard cleaning (fiscal year conversion)
        df = super()._clean(df)

        # Clean numeric columns (remove commas, convert to Int64)
        for col in self.NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .pipe(pd.to_numeric, errors="coerce")
                    .astype("Int64")
                )

        return df
