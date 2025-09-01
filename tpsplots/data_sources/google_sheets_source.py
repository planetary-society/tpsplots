"""
Google Sheets Data Source
=========================

A simplified base class for loading data from Google Sheets CSV exports.
Unlike NASABudget, this class focuses on simple data loading and type casting
without inflation adjustment or complex fiscal year handling.

Usage Example
-------------
```python
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

class MyDataSource(GoogleSheetsSource):
    URL = "https://docs.google.com/spreadsheets/d/.../export?format=csv"
    
    # Optional: Override specific column types after pandas auto-detection
    CAST = {
        "Date": "datetime64[ns]",
        "Category": "category",
        "ID": "str"  # Keep as string even if numeric
    }
    
    # Optional: Select specific columns
    COLUMNS = ["Date", "Category", "Value"]
    
    # Optional: Rename columns
    RENAMES = {"Value": "Amount"}

# Use the data source
data = MyDataSource()
df = data.data()  # Get pandas DataFrame
dates = data.date  # Access columns as attributes
```
"""

from __future__ import annotations

import io
import logging
from datetime import timedelta
from functools import cached_property
from pathlib import Path
from typing import Any, List

import pandas as pd
import requests
from cachier import cachier

logger = logging.getLogger(__name__)


class GoogleSheetsSource:
    """
    Base class for loading data from Google Sheets CSV exports.
    
    This class provides a simplified interface for:
    - Loading CSV data from Google Sheets URLs
    - Automatic type inference via pandas
    - Optional type casting overrides
    - Column selection and renaming
    - Attribute-style column access
    
    Subclasses should define:
    - URL (str): The Google Sheets CSV export URL (required)
    - CAST (Dict[str, str]): Column type overrides (optional)
    - COLUMNS (List[str]): Columns to keep (optional)
    - RENAMES (Dict[str, str]): Column renames (optional)
    """
    
    # Type mapping for simple type names to pandas dtypes
    TYPE_MAPPING = {
        "int": "int64",
        "float": "float64",
        "str": "object",
        "string": "object",
        "bool": "bool",
        "datetime": "datetime64[ns]",
        "date": "datetime64[ns]",
    }
    
    def __init__(self, cache_dir: Path | None = None) -> None:
        """
        Initialize the GoogleSheetsSource instance.
        
        Args:
            cache_dir: Optional directory to cache downloaded CSV files
        """
        # Get URL from class attribute
        if not hasattr(self.__class__, 'URL'):
            raise ValueError(f"{self.__class__.__name__} must define a URL attribute")
        
        self._url = self.__class__.URL
        self._cache_dir = cache_dir
    
    def data(self) -> pd.DataFrame:
        """
        Return the processed DataFrame.
        
        Returns:
            A copy of the processed pandas DataFrame
        """
        return self._df.copy(deep=True)
    
    def columns(self) -> List[str]:
        """
        Return list of column names in the processed DataFrame.
        
        Returns:
            List of column names
        """
        return list(self._df.columns)
    
    def __getattr__(self, name: str) -> List[Any]:
        """
        Provide attribute-style access to DataFrame columns.
        
        Args:
            name: The attribute name to access
            
        Returns:
            List of values from the corresponding column
            
        Raises:
            AttributeError: If the name doesn't match any column
        """
        # Convert attribute name to match potential column names
        # (e.g., 'award_date' could match 'Award Date')
        normalized_name = name.replace('_', ' ').title()
        
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
    
    @cached_property
    def _df(self) -> pd.DataFrame:
        """
        Load and process the data into a DataFrame.
        
        This property is computed once and cached. It orchestrates:
        1. Reading CSV from URL
        2. Column selection (if COLUMNS defined)
        3. Column renaming (if RENAMES defined)
        4. Type casting overrides (if CAST defined)
        
        Returns:
            The processed pandas DataFrame
        """
        # Read the CSV data
        df = self._read_csv()
        
        # Select columns if specified
        if columns := getattr(self.__class__, 'COLUMNS', None):
            missing = [col for col in columns if col not in df.columns]
            if missing:
                logger.warning(f"Columns not found in data: {missing}")
            existing = [col for col in columns if col in df.columns]
            df = df[existing]
        
        # Rename columns if specified
        if renames := getattr(self.__class__, 'RENAMES', None):
            df = df.rename(columns=renames)
        
        # Apply type casting overrides
        df = self._cast_columns(df)
        
        return df
    
    @staticmethod
    @cachier(stale_after=timedelta(hours=24))
    def _fetch_csv_content(url: str) -> str:
        """
        Fetch CSV content from URL with caching.
        
        Args:
            url: The URL to fetch
            
        Returns:
            The CSV content as a string
        """
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    
    def _read_csv(self) -> pd.DataFrame:
        """
        Read CSV data from the Google Sheets URL.
        
        Uses caching if cache_dir is specified.
        
        Returns:
            DataFrame with data from CSV
        """
        # Check cache if enabled
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            # Create cache filename from URL (use last part of sheet ID)
            cache_name = self._url.split('/')[-2][:20] + '.csv'
            cache_path = self._cache_dir / cache_name
            
            if cache_path.exists():
                logger.debug(f"Reading from cache: {cache_path}")
                return pd.read_csv(cache_path)
        
        # Fetch from URL
        logger.debug(f"Fetching data from: {self._url}")
        csv_content = self._fetch_csv_content(self._url)
        
        # Parse CSV with pandas auto-detection
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Save to cache if enabled
        if self._cache_dir:
            logger.debug(f"Caching data to: {cache_path}")
            df.to_csv(cache_path, index=False)
        
        return df
    
    def _cast_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply type casting overrides from CAST attribute.
        
        This method only applies casting for columns explicitly defined in CAST,
        leaving other columns with their pandas-inferred types.
        
        Args:
            df: The input DataFrame
            
        Returns:
            DataFrame with type overrides applied
        """
        # Get CAST dictionary from class
        cast_dict = getattr(self.__class__, 'CAST', None)
        if not cast_dict:
            return df
        
        df = df.copy()
        
        for col, dtype in cast_dict.items():
            if col not in df.columns:
                logger.warning(f"CAST column '{col}' not found in DataFrame")
                continue
            
            # Normalize simple type names to pandas dtypes
            dtype = self.TYPE_MAPPING.get(dtype, dtype)
            
            try:
                # Special handling for datetime
                if 'datetime' in str(dtype):
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                else:
                    df[col] = df[col].astype(dtype, errors='ignore')
                logger.debug(f"Cast column '{col}' to {dtype}")
            except Exception as e:
                logger.error(f"Failed to cast column '{col}' to {dtype}: {e}")
        
        return df
