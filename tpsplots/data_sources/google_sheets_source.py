"""
Google Sheets Data Source
=========================

A class for loading data from Google Sheets CSV exports, built on
:class:`~tpsplots.data_sources.tabular_data_source.TabularDataSource`.

Inherits the full data-processing pipeline (column selection, renaming,
type casting, currency cleaning, fiscal-year conversion) and adds
Google-Sheets-specific URL resolution and CSV fetching.

Usage Examples
--------------

Direct Instantiation (for one-off sheets):
```python
from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

# Simple usage with just a URL
data_source = GoogleSheetsSource(url="https://docs.google.com/spreadsheets/d/.../export?format=csv")
df = data_source.data()

# With additional configuration
data_source = GoogleSheetsSource(
    url="https://docs.google.com/spreadsheets/d/.../export?format=csv",
    columns=["Date", "Category", "Value"],  # Select specific columns
    renames={"Value": "Amount"},  # Rename columns
    cast={"Date": "datetime", "ID": "str"},  # Override types
)
df = data_source.data()
values = data_source.amount  # Access renamed column as attribute
```

Subclassing (for reusable data sources):
```python
class MyDataSource(GoogleSheetsSource):
    URL = "https://docs.google.com/spreadsheets/d/.../export?format=csv"

    # Optional: Override specific column types after pandas auto-detection
    CAST = {
        "Date": "datetime64[ns]",
        "Category": "category",
        "ID": "str",  # Keep as string even if numeric
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

import pandas as pd
import requests

from tpsplots.data_sources.tabular_data_source import TabularDataSource

logger = logging.getLogger(__name__)


class GoogleSheetsSource(TabularDataSource):
    """
    Load data from Google Sheets CSV exports.

    Inherits from :class:`TabularDataSource` which provides column selection,
    renaming, type casting, currency cleaning, and fiscal-year conversion.

    Can be used in two ways:

    1. **Direct instantiation** — pass ``url`` and optional processing params.
    2. **Subclassing** — set class attributes ``URL``, ``CAST``, ``COLUMNS``,
       ``RENAMES``, ``AUTO_CLEAN_CURRENCY``.

    For direct instantiation, pass parameters to ``__init__``:
    - url: The Google Sheets CSV export URL
    - cast, columns, renames, auto_clean_currency, fiscal_year_column:
      forwarded to :class:`TabularDataSource`.

    For subclassing, define class attributes:
    - URL (str): The Google Sheets CSV export URL
    - CAST (Dict[str, str]): Column type overrides (optional)
    - COLUMNS (List[str]): Columns to keep (optional)
    - RENAMES (Dict[str, str]): Column renames (optional)
    """

    TRUNCATE_AT = "Total:"

    def __init__(self, url: str | None = None, **kwargs) -> None:
        """
        Initialize the GoogleSheetsSource instance.

        Args:
            url: Google Sheets CSV export URL (optional if defined as class
                attribute ``URL``).
            **kwargs: Forwarded to :class:`TabularDataSource` — accepts
                ``cast``, ``columns``, ``renames``, ``auto_clean_currency``,
                and ``fiscal_year_column``.
        """
        # URL resolution: parameter takes precedence over class attribute
        self._url = url or getattr(self.__class__, "URL", None)
        if not self._url:
            raise ValueError(
                f"{self.__class__.__name__} must provide URL either as parameter or class attribute"
            )

        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # TabularDataSource implementation
    # ------------------------------------------------------------------

    def _read_raw_df(self) -> pd.DataFrame:
        """
        Read CSV data from the Google Sheets URL.

        Returns:
            DataFrame with data from CSV.
        """
        logger.debug(f"Fetching data from: {self._url}")
        csv_content = self._fetch_csv_content(self._url)
        return pd.read_csv(io.StringIO(csv_content))

    # ------------------------------------------------------------------
    # Google-Sheets-specific helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_csv_content(url: str) -> str:
        """
        Fetch CSV content from URL.

        Args:
            url: The URL to fetch.

        Returns:
            The CSV content as a string.
        """
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
