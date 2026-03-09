"""
CSV Data Source
================

A class for loading data from local CSV files, built on
:class:`~tpsplots.data_sources.tabular_data_source.TabularDataSource`.

Inherits the full data-processing pipeline (column selection, renaming,
type casting, currency cleaning, fiscal-year conversion) and adds
CSV-file-specific reading via :func:`pandas.read_csv`.

Usage Examples
--------------

Direct Instantiation:
```python
from tpsplots.data_sources.csv_source import CSVSource

# Simple usage with just a path
data_source = CSVSource(csv_path="data/missions.csv")
df = data_source.data()

# With additional configuration
data_source = CSVSource(
    csv_path="data/missions.csv",
    columns=["Name", "Launch Date", "Cost"],
    renames={"Cost": "Total Cost"},
    cast={"Launch Date": "datetime"},
)
df = data_source.data()
```
"""

from __future__ import annotations

import logging

import pandas as pd

from tpsplots.data_sources.tabular_data_source import TabularDataSource

logger = logging.getLogger(__name__)


class CSVSource(TabularDataSource):
    """
    Load data from a local CSV file.

    Inherits from :class:`TabularDataSource` which provides column selection,
    renaming, type casting, currency cleaning, and fiscal-year conversion.

    Pass ``csv_path`` to ``__init__`` along with any optional processing
    parameters (``cast``, ``columns``, ``renames``, ``auto_clean_currency``,
    ``fiscal_year_column``), all of which are forwarded to
    :class:`TabularDataSource`.
    """

    def __init__(self, csv_path: str | None = None, **kwargs) -> None:
        """
        Initialize the CSVSource instance.

        Args:
            csv_path: Path to a local CSV file.
            **kwargs: Forwarded to :class:`TabularDataSource` — accepts
                ``cast``, ``columns``, ``renames``, ``auto_clean_currency``,
                and ``fiscal_year_column``.

        Raises:
            ValueError: If *csv_path* is not provided.
        """
        if not csv_path:
            raise ValueError("CSVSource requires a csv_path argument")

        self._csv_path = csv_path
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # TabularDataSource implementation
    # ------------------------------------------------------------------

    def _read_raw_df(self) -> pd.DataFrame:
        """
        Read CSV data from the local file.

        Returns:
            DataFrame with data from the CSV file.
        """
        logger.debug(f"Reading CSV from: {self._csv_path}")
        return pd.read_csv(self._csv_path)
