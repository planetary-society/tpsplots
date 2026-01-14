"""
Space Science Missions Data Source
===================================

This module provides a data source for space science missions data from a Google Sheet.
It includes custom transformations for mass, cost data, and inflation adjustments.

Key Features
-----------
- Automatic mass column processing (rename, clean suffix, convert to integer)
- LCC cost processing (strip currency symbols, convert to float)
- NNSI inflation adjustment based on mission launch year - 1

Usage Example
------------
```python
from tpsplots.data_sources.space_science_missions import SpaceScienceMissions

# Create a data source instance
missions = SpaceScienceMissions()

# Get the processed DataFrame
df = missions.data()

# Access columns as attributes
mass_values = missions.mass_kg  # Access renamed "Mass (kg)" column
lcc_values = missions.lcc_m  # Access "LCC ($M)" column
```
"""

from __future__ import annotations

import logging
from functools import cached_property

import pandas as pd

from .google_sheets_source import GoogleSheetsSource
from .inflation import NNSI

logger = logging.getLogger(__name__)


def _get_prior_fy() -> int:
    """
    Calculate the prior fiscal year based on the current date.

    The fiscal year starts in October.

    Returns:
        The prior fiscal year as an integer.
    """
    from datetime import date

    import pandas as pd

    last_year_date = date.today() - pd.DateOffset(years=1)
    return last_year_date.year + (last_year_date.month >= 10)


class SpaceScienceMissions(GoogleSheetsSource):
    """
    Data source for space science missions from Google Sheets.

    This class loads mission data and performs several transformations:
    1. Renames and cleans the "Mass" column to "Mass (kg)"
    2. Processes the "LCC ($M)" column to remove currency formatting
    3. Applies NNSI inflation adjustment to LCC based on launch year - 1

    The inflation adjustment uses the mission's launch year minus 1 as the
    source year, adjusting to the current prior fiscal year.
    """

    URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1ag7otfTfElrFz-yRZEdp-sLxlwkS_p7gRvnD1tVo7fE/"
        "export?format=csv"
    )

    def __init__(self) -> None:
        """
        Initialize the SpaceScienceMissions data source.
        """
        super().__init__(url=self.URL)

    @cached_property
    def _df(self) -> pd.DataFrame:
        """
        Load and process the DataFrame with custom transformations.

        This method overrides the parent class to add specific transformations:
        - Mass column renaming and cleaning
        - LCC column currency removal
        - NNSI inflation adjustment based on launch date

        Returns:
            The processed pandas DataFrame
        """
        # Load the raw CSV data
        df = self._read_csv()

        # Apply transformations
        df = self._transform_mass_column(df)
        df = self._transform_lcc_column(df)
        df = self._apply_inflation_adjustment(df)

        return df

    def _transform_mass_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the Mass column: rename, strip suffix, convert to float.

        If a "Mass" column exists:
        1. Rename it to "Mass (kg)"
        2. Strip " kg" suffix from all values
        3. Convert to float type
        4. Handle empty values as NaN

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with transformed Mass column
        """
        if "Mass" not in df.columns:
            return df

        df = df.copy()

        # Rename the column
        df = df.rename(columns={"Mass": "Mass (kg)"})

        # Clean and convert the values
        df["Mass (kg)"] = (
            df["Mass (kg)"]
            .astype(str)
            .str.replace(" kg", "", regex=False)
            .str.strip()
            .replace("", pd.NA)
            .replace("nan", pd.NA)
        )

        # Convert to float
        df["Mass (kg)"] = pd.to_numeric(df["Mass (kg)"], errors="coerce")

        logger.debug("Transformed Mass column to Mass (kg)")
        return df

    def _transform_lcc_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the LCC (M$) column: strip currency symbols, convert to float.

        If "LCC (M$)" column exists:
        1. Strip leading "$" from values
        2. Convert to float type
        3. Handle empty values as NaN

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with transformed LCC column
        """
        if "LCC (M$)" not in df.columns:
            return df

        df = df.copy()

        # Clean and convert the values
        df["LCC (M$)"] = (
            df["LCC (M$)"]
            .astype(str)
            .str.lstrip("$")
            .str.strip()
            .replace("", pd.NA)
            .replace("nan", pd.NA)
        )

        # Convert to float
        df["LCC (M$)"] = pd.to_numeric(df["LCC (M$)"], errors="coerce")

        logger.debug("Transformed LCC (M$) column")
        return df

    def _apply_inflation_adjustment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply NNSI inflation adjustment to LCC based on launch year - 1.

        Uses the "Mission Launch Date" column to extract the year, then
        calculates inflation-adjusted LCC values using (launch_year - 1)
        as the source year.

        Creates a new column: "LCC (M$)_adjusted_nnsi"

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with added inflation-adjusted column
        """
        # Check if required columns exist
        if "Mission Launch Date" not in df.columns or "LCC (M$)" not in df.columns:
            logger.warning("Cannot apply inflation adjustment: required columns missing")
            return df

        df = df.copy()

        # Extract year from launch date
        launch_dates = pd.to_datetime(df["Mission Launch Date"], errors="coerce")
        launch_years = launch_dates.dt.year

        # Calculate adjustment year (launch_year - 1)
        adjustment_years = launch_years - 1

        # Initialize NNSI adjuster for current prior fiscal year
        nnsi = NNSI(year=str(_get_prior_fy()))

        # Apply inflation adjustment row by row
        def adjust_row(row_idx):
            """Helper to adjust a single row's LCC value."""
            adj_year = adjustment_years.iloc[row_idx]
            lcc_value = df["LCC (M$)"].iloc[row_idx]

            # Only adjust if we have valid year and LCC value
            if pd.notna(adj_year) and pd.notna(lcc_value):
                try:
                    # Convert year to int for the calc method
                    return nnsi.calc(str(int(adj_year)), lcc_value)
                except (ValueError, KeyError) as e:
                    logger.debug(f"Could not adjust row {row_idx}: {e}")
                    return lcc_value
            else:
                # Return original value if we can't adjust
                return lcc_value

        # Apply adjustment to all rows
        df["LCC (M$)_adjusted_nnsi"] = [adjust_row(i) for i in range(len(df))]

        logger.debug("Applied NNSI inflation adjustment to LCC (M$)")
        return df
