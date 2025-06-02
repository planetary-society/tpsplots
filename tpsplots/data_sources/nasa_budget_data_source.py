"""
NASA Budget Data Source Documentation
=====================================

This module provides classes for handling NASA budget data from various sources.
It supports both string and datetime fiscal year representations and provides
automatic inflation adjustments.

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

# Create a data source instance
budget = Historical()

# Get the cleaned and processed DataFrame
df = budget.data()

# Access values via attribute-style getters
fy = budget.fiscal_year  # Returns list of fiscal years
requests = budget.pbr  # Returns list of presidential budget requests

# Get inflation-adjusted values
adj_requests = budget.pbr_adjusted_nnsi  # Adjusted using NASA New-Start Index
```

Working with Fiscal Years
------------------------
The module handles fiscal years in both string and datetime formats:

- When loading data from CSV sources, the fiscal year column is automatically
  converted to datetime objects for easier plotting and manipulation.
  
- Special cases like the "1976 TQ" (Transition Quarter) are preserved as strings.

- Inflation adjustment calculations can use either string or datetime inputs
  and will produce consistent results with either format.

- When converting fiscal years to strings for display, use standard string
  formatting: `f"{fiscal_year:%Y}"` for a four-digit year representation.
"""

from __future__ import annotations

import io
import re
import ssl
from datetime import date, datetime
from functools import cached_property
from pathlib import Path
from typing import Callable, List, Any

import certifi
import pandas as pd
import requests
from urllib.error import URLError

# Assumed external library for inflation adjustments
from .inflation import NNSI, GDP

import logging

logger = logging.getLogger(__name__)

# ─────────────────────────── base class ────────────────────────────
class NASABudget:
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
    """
    # Regex to find and remove currency symbols, commas, and 'M' or 'B' suffixes
    _CURRENCY_RE = re.compile(r"[\$,]|\s*[MB]$", flags=re.IGNORECASE)

    # ── core API ────────────────────────────────────────────────────
    def __init__(self, csv_source: str | Path, *, cache_dir: Path | None = None) -> None:
        """
        Initializes the NASABudget instance.

        The data loading and processing pipeline is triggered lazily when
        the `_df` cached property is first accessed.

        Args:
            csv_source: The path to a local CSV file or a URL of a CSV file.
            cache_dir: An optional directory to cache downloaded CSV files.
        """
        self._csv_source = str(csv_source)
        self._cache_dir = cache_dir

    def data(self) -> pd.DataFrame:
        """
        Return the fully cleaned & augmented DataFrame.

        Returns:
            A deep copy of the internal pandas DataFrame containing the
            processed NASA budget data.
        """
        return self._df.copy(deep=True)

    def columns(self) -> List[str]:
        """
        Return a list of column names in the processed DataFrame.

        Returns:
            A list of strings representing the column names.
        """
        return list(self._df.columns)

    def __getattr__(self, name: str) -> List[Any]:
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
        subclass and dynamically creates two attributes for each:
        - A raw attribute (e.g., `appropriation`) returning the nominal list.
        - An adjusted attribute (e.g., `appropriation_adjusted`) returning
          the inflation-adjusted list based on specified type and year.

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
            # Create the adjusted attribute name
            adj_attr = f"{attr}_adjusted"
            if adj_attr not in cls.__dict__:
                setattr(cls, adj_attr, cls._mk_adj(col))

    @classmethod
    def _mk_raw(cls, col: str) -> Callable[["NASABudget"], List[float]]:
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

    @classmethod
    def _mk_adj(cls, col: str) -> Callable:
        """
        Creates a getter function for an inflation-adjusted monetary column.

        This function returns a callable that, when called on a NASABudget
        instance, calculates and returns the specified column's data adjusted
        for inflation. The adjustment type ("nnsi" or "gdp") and target year
        can be specified.

        Args:
            col: The name of the column in the DataFrame to adjust.

        Returns:
            A callable that takes a NASABudget instance and optional type/year
            arguments, returning a list of adjusted float values.
        """
        def getter(self, *, type: str = "nnsi", year: int | None = None) -> List[float]:
            """
            Getter function for adjusted monetary columns.

            Calculates the inflation-adjusted values for the column.

            Args:
                type: The type of inflation index to use ("nnsi" or "gdp").
                      Defaults to "nnsi".
                year: The target fiscal year for adjustment. If None, defaults
                      to the prior fiscal year based on the current date.

            Returns:
                A list of floats representing the inflation-adjusted values.

            Raises:
                KeyError: If an invalid adjustment type is provided.
            """
            # Detect the fiscal year column name
            fy = self._fy_col()
            # Get the appropriate adjuster object (NNSI or GDP) based on type
            # Raises KeyError if type is invalid
            adj = _ADJUSTERS[type.lower()]
            # Calculate the inflation multiplier for each row based on its fiscal year
            # The multiplier converts the value from the row's FY to the adjuster's target year (prior FY)
            # Ensure the fiscal year value is passed as a string to the calc method
            mult = self._df[fy].apply(lambda v: adj.calc(str(v), 1.0))
            # Apply the multiplier to the column values and return as a list
            return (self._df[col] * mult).tolist()
        # Return the inner getter function
        return getter

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
        cleaned = self._clean(raw)
        # Add inflation-adjusted columns
        return self._add_adjusted_cols(cleaned)

    # ── I/O helpers ────────────────────────────────────────────────
    def _read_csv(self) -> pd.DataFrame:
        """
        Reads the CSV data from the source, potentially using a cache.

        If a cache directory is specified and the cached file exists, it reads
        from the cache. Otherwise, it reads from the specified source (local
        path or URL). If reading from a URL and a cache directory is provided,
        it saves the downloaded data to the cache.

        Returns:
            A pandas DataFrame containing the raw data from the CSV source.

        Raises:
            URLError, ssl.SSLError, requests.exceptions.RequestException:
                If the data cannot be fetched from the URL.
            FileNotFoundError: If the local file does not exist.
        """
        # Check if caching is enabled and a cached file exists
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            dest = self._cache_dir / Path(self._csv_source).name
            if dest.exists():
                logger.info(f"Reading from cache: {dest}") # Added for visibility
                return pd.read_csv(dest)

        logger.info(f"Reading from source: {self._csv_source}") # Added for visibility
        try:
            # Try reading directly (works for local files and some URLs)
            df = pd.read_csv(self._csv_source)
        except (URLError, ssl.SSLError):
            # If direct read fails (often for HTTPS URLs), use requests
            logger.warning("Direct read failed, attempting with requests...") # Added for visibility
            try:
                # Fetch content using requests, verifying SSL certs
                response = requests.get(self._csv_source, timeout=30, verify=certifi.where())
                response.raise_for_status() # Raise an exception for bad status codes
                text = response.text
                # Read the text content into a DataFrame
                df = pd.read_csv(io.StringIO(text))
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching data with requests: {e}") # Added for visibility
                raise 

        # If caching is enabled, save the downloaded DataFrame to the cache
        if self._cache_dir:
            cache_path = Path(self._cache_dir, Path(self._csv_source).name)
            logger.info(f"Caching data to: {cache_path}") # Added for visibility
            cache_path.write_bytes(
                df.to_csv(index=False).encode() # Convert DataFrame to CSV string, then bytes
            )
        return df

    # ── cleaning helpers ───────────────────────────────────────────
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
        df = df.copy() # Work on a copy to avoid modifying the original DataFrame

        # Clean currency-like columns: remove symbols, commas, and M/B suffixes,
        # then convert to float and multiply by 1,000,000 if M/B was present.
        for col in df.select_dtypes("object"):
            # Check if the column contains '$' characters (indicating currency)
            # OR if the column is listed in MONETARY_COLUMNS
            if (
            df[col].astype(str).str.contains(r"\$", na=False).any()
            or (hasattr(self, "MONETARY_COLUMNS") and col in getattr(self, "MONETARY_COLUMNS", []))
            ):
                df[col] = (
                    df[col]
                    .astype(str) # Ensure column is string type for regex operations
                    .str.replace(self._CURRENCY_RE, "", regex=True) # Remove currency symbols, commas, M/B
                    .astype(float, errors="ignore") # Convert to float, ignoring errors (non-numeric become NaN)
                    .mul(1_000_000) # Multiply by 1 million to convert to whole dollars
                    .astype("float64")
                )

        # Clean date-style columns: convert to datetime objects.
        # Identifies columns ending with 'date', 'signed', or 'updated' (case-insensitive).
        for col in df.columns:
            if re.search(r"(date|signed|updated)$", str(col), flags=re.I):
                # Convert to datetime, coercing errors to NaT (Not a Time)
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

        # Clean fiscal-year / year columns: normalize format and handle "1976 TQ".
        # Identifies columns matching FY followed by 2-4 digits or names like 'fiscal year', 'fy', 'year'.
        # Modified to keep 4-digit years as strings.
        def norm(x):
            """Helper function to normalize fiscal year values, keeping them as strings."""
            if pd.isna(x):
                return pd.NA # Return pandas NA for missing values
            s = str(x).strip() # Convert to string and remove leading/trailing whitespace
            if "TQ" in s.upper():
                return "1976 TQ" # Preserve the special '1976 TQ' string
            if s.isdigit() and len(s) == 4:
                return datetime(int(s), 1, 1)
            return pd.NA # Return pandas NA for any other format

        for col in df.columns:
            if re.fullmatch(r"FY\d{2,4}", str(col), flags=re.I) or str(col).lower() in {
                "fiscal year",
                "fy",
                "year",
            }:
                # Apply the normalization function to the column
                df[col] = df[col].apply(norm)

        return df

    def _add_adjusted_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds inflation-adjusted columns to the DataFrame.

        For each column listed in `MONETARY_COLUMNS`, two new columns are added:
        - `{column_name}_adjusted_nnsi`: Adjusted using the NNSI index.
        - `{column_name}_adjusted_gdp`: Adjusted using the GDP index.
        The adjustment is performed to the prior fiscal year.

        Args:
            df: The input pandas DataFrame.

        Returns:
            A new DataFrame with the added adjusted columns.
        """
        df = df.copy() # Work on a copy
        # Detect the fiscal year column to use for adjustments
        fy_col = self._detect_fy(df)
        if not fy_col:
            return df
        
        # Get the list of columns to adjust from the subclass
        mons = getattr(self.__class__, "MONETARY_COLUMNS", [])

        # If no monetary columns are defined, return the DataFrame as is
        if not mons:
            return df

        # Calculate the inflation multipliers for NNSI and GDP for each fiscal year in the DataFrame
        # Pass the fiscal year values directly to the calc method - it now handles both strings and datetimes
        nnsi_mult = df[fy_col].apply(lambda v: _ADJUSTERS["nnsi"].calc(v, 1.0))
        gdp_mult = df[fy_col].apply(lambda v: _ADJUSTERS["gdp"].calc(v, 1.0))

        # Apply the multipliers to each monetary column and add the new adjusted columns
        for col in mons:
            if col in df.columns: # Ensure the column exists in the DataFrame
                # Calculate product. If multiplier is NaN, product is NaN.
                try:
                    product_nnsi = df[col] * nnsi_mult
                except TypeError as e:
                    logger.error(f"Can't multiply column '{col}': {e}")
                    product_nnsi = pd.Series([pd.NA] * len(df[col]), index=df.index)
                
                try:
                    product_gdp = df[col] * gdp_mult
                except TypeError as e:
                    logger.error(f"Can't multiply column '{col}': {e}")
                    product_gdp = pd.Series([pd.NA] * len(df[col]), index=df.index)
                    
                # Where product is NaN (likely due to a NaN multiplier),
                # fill with the original value from df[col].
                # Then ensure the final column is of type float64.
                df[f"{col}_adjusted_nnsi"] = product_nnsi.fillna(df[col]).astype("float64")
                df[f"{col}_adjusted_gdp"] = product_gdp.fillna(df[col]).astype("float64")
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
            else:
                return None
        logger.warning("No fiscal-year column detected.")

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


# single shared inflation adjusters (reuse everywhere)
# Initialize NNSI and GDP adjusters, targeting the prior fiscal year.
# These instances are created once when the module is imported.
# The year is passed as a string, which aligns with the updated norm function.
_ADJUSTERS = {
    "nnsi": NNSI(year=str(NASABudget._prior_fy())),
    "gdp":  GDP(year=str(NASABudget._prior_fy())),
}


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
    COLUMNS = [
        "Fiscal Year",
        "Presidential Administration",
        "White House Budget Release Date",
        "White House Budget Submission",
        "White House Budget Projection",
        "Appropriation",
        "Outlays",
        "% of U.S. Spending",
        "% of U.S. Discretionary Spending",
    ]
    # Define how to rename columns after loading
    RENAMES = {"White House Budget Submission": "PBR"}
    # Define which columns contain monetary values that need inflation adjustment
    MONETARY_COLUMNS = ["PBR", "Appropriation", "Outlays"]

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        """
        Initializes the Historical budget data instance.

        Args:
            cache_dir: An optional directory to cache the downloaded CSV file.
        """
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL, cache_dir=cache_dir)


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
    COLUMNS = ["Fiscal Year", "Astrophysics", "Planetary Science", "Earth Science", "Heliophysics",
               "Astrophysics Proposed", "Planetary Science Proposed", "Earth Science Proposed", "Heliophysics Proposed"]
    MONETARY_COLUMNS = ["Astrophysics", "Planetary Science", "Earth Science", "Heliophysics",
                        "Astrophysics Proposed", "Planetary Science Proposed", "Earth Science Proposed", "Heliophysics Proposed"]

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        """
        Initializes the Science budget data instance.

        Args:
            cache_dir: An optional directory to cache the downloaded CSV file.
        """
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL, cache_dir=cache_dir)


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
    COLUMNS = ["Fiscal Year", "Aeronautics", "HSF Exploration", "LEO Space Operations",
               "STMD", "SMD", "Education/STEM Outreach", "Cross Agency Support/CECR"]
    RENAMES = {
            "Cross Agency Support/CECR": "Facilities, IT, & Salaries",
            "Education/STEM Outreach": "STEM Education",
            "STMD": "Space Technology",
            "HSF Exploration": "Deep Space Exploration Systems",
            "SMD": "Science",
        }
    MONETARY_COLUMNS = ["Aeronautics", "Space Technology", "Deep Space Exploration Systems", "LEO Space Operations",
               "Science", "STEM Education", "Facilities, IT, & Salaries"]

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        """
        Initializes the Directorates budget data instance.

        Args:
            cache_dir: An optional directory to cache the downloaded CSV file.
        """
        # Call the base class constructor with the specific CSV URL
        super().__init__(self.CSV_URL, cache_dir=cache_dir)

class Science(NASABudget):
    CSV_URL = ("https://docs.google.com/spreadsheets/d/"
               "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/"
               "export?format=csv&gid=1298630212")
    
    COLUMNS = ["Fiscal Year", "NASA Science (millions of $)","FY 2026 PBR"]
    RENAMES = {"NASA Science (millions of $)": "NASA Science"}
    MONETARY_COLUMNS = ["NASA Science", "FY 2026 PBR"]
    
    def __init__(self, *, cache_dir: Path | None = None) -> None:
        super().__init__(self.CSV_URL, cache_dir=cache_dir)