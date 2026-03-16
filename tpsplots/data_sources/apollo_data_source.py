"""Apollo-era spending data sources.

Loads spending data for Project Apollo and related programs from Google Sheets
CSV exports. All values in the source are in thousands of dollars and are
converted to absolute dollars during cleaning.

Note: Inflation adjustment is NOT automatic. Use InflationAdjustmentProcessor
explicitly in controllers to apply inflation adjustments to monetary columns.

Usage Example
-------------
```python
from tpsplots.data_sources.apollo_data_source import ApolloSpending

apollo = ApolloSpending()
df = apollo.data()

# For inflation-adjusted values:
from tpsplots.processors import InflationAdjustmentConfig, InflationAdjustmentProcessor

config = InflationAdjustmentConfig(nnsi_columns=ApolloSpending.MONETARY_COLUMNS)
df = InflationAdjustmentProcessor(config).process(df)
```
"""

from __future__ import annotations

import io
import logging
from functools import cached_property
from typing import ClassVar

import certifi
import pandas as pd
import requests

from tpsplots.data_sources.nasa_budget_data_source import NASABudget
from tpsplots.data_sources.truncate_rows_mixin import TruncateRowsMixin
from tpsplots.utils.currency_processing import clean_currency_column

logger = logging.getLogger(__name__)

# Base spreadsheet ID shared by all Apollo-era tabs.
_SPREADSHEET_ID = "1QW8MaPWa2YXDik52h4M0LN4SVc_tINoFEwashbaOjgE"
_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{_SPREADSHEET_ID}/export?format=csv&gid="


# ────────────────────────── shared base ──────────────────────────
class _ApolloBase(TruncateRowsMixin, NASABudget):
    """Base class for Apollo-era spending data sources.

    Handles conventions shared across all tabs in the Apollo spreadsheet:

    - Currency values are in **thousands of dollars** (multiplier = 1,000).
    - A trailing "Totals" row is truncated automatically via ``TruncateRowsMixin``.
    """

    TRUNCATE_AT = "Totals"

    def _clean_currency_column(self, series: pd.Series) -> pd.Series:
        """Clean currency column converting from thousands to dollars."""
        return clean_currency_column(series, multiplier=1_000)

    @cached_property
    def _df(self) -> pd.DataFrame:
        """Load, truncate, and clean the data."""
        raw = self._read_csv()
        raw = self._truncate_rows(raw)

        if subset := getattr(self.__class__, "COLUMNS", None):
            raw = raw[subset]
        if ren := getattr(self.__class__, "RENAMES", None):
            raw = raw.rename(columns=ren)

        return self._clean(raw)


# ────────────────────────── concrete sheets ──────────────────────
class ApolloSpending(_ApolloBase):
    """Project Apollo spending data from FY 1960-1973.

    Loads from a Google Sheets CSV export containing annual cost breakdowns
    for the Apollo program across spacecraft, launch vehicles, mission
    support, facilities, and related programs.

    The source CSV has a junk category-header row above the real column
    headers, so ``_read_csv`` skips the first row.  A trailing "Totals"
    row (and everything after it) is removed automatically.
    """

    CSV_URL = _SHEET_URL + "1577405277"

    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "NASA Total Obligations",
        "Lunar Effort Total",
        "Annual Direct Costs",
        "Spacecraft",
        "CSM",
        "LM",
        "Guidance & Navigation",
        "Instrumentation & Spacecraft Support",
        "Supporting Development",
        "Saturn Launch Vehicles",
        "Saturn C-I/I",
        "Saturn IB",
        "Saturn V",
        "Engine Development",
        "Support, Development, & Operations",
        "Mission Support",
        "Mission Operations",
        "Program Development Studies",
        "Annual Indirect Costs",
        "Construction of Facilities",
        "Facilities Operations and Overhead",
        "Tracking and Data R&D",
        "Annual Related Programs Cost",
        "Robotic Lunar Missions",
        "Project Gemini",
    ]

    PERCENTAGE_COLUMNS: ClassVar[list[str]] = ["Lunar effort % of NASA"]

    def __init__(self) -> None:
        """Initialize the Apollo spending data instance."""
        super().__init__(self.CSV_URL)

    def _read_csv(self) -> pd.DataFrame:
        """Read CSV, skipping the junk category-header first row.

        The source spreadsheet has a merged-cell category row (row 1) that
        becomes meaningless comma-separated values in the CSV export.  The
        real column headers are in row 2.
        """
        response = requests.get(self._csv_source, timeout=30, verify=certifi.where())
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), skiprows=1)


class RoboticLunarProgramSpending(_ApolloBase):
    """Robotic lunar program spending (Ranger, Surveyor, Lunar Orbiter)."""

    CSV_URL = _SHEET_URL + "377240563"

    COLUMNS: ClassVar[list[str]] = [
        "Year",
        "Ranger",
        "Surveyor",
        "Lunar Orbiter",
        "Total Robotic",
    ]

    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Ranger",
        "Surveyor",
        "Lunar Orbiter",
        "Total Robotic",
    ]

    def __init__(self) -> None:
        super().__init__(self.CSV_URL)


class ProjectGemini(_ApolloBase):
    """Project Gemini spending data."""

    CSV_URL = _SHEET_URL + "725456464"

    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Spacecraft",
        "Support",
        "Launch Vehicle",
        "Total",
    ]

    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Spacecraft",
        "Support",
        "Launch Vehicle",
        "Total",
    ]

    def __init__(self) -> None:
        super().__init__(self.CSV_URL)


class FacilitiesConstructionSpending(_ApolloBase):
    """Apollo facilities construction spending data."""

    CSV_URL = _SHEET_URL + "849026288"

    COLUMNS: ClassVar[list[str]] = [
        "Year",
        "Manned Spaceflight Ground Facilities",
        "Office of Tracking and Data Acquisition Facilities",
        "Total Facilities",
    ]

    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Manned Spaceflight Ground Facilities",
        "Office of Tracking and Data Acquisition Facilities",
        "Total Facilities",
    ]

    def __init__(self) -> None:
        super().__init__(self.CSV_URL)


class SaturnLaunchVehicles(ApolloSpending):
    """Saturn-family launch vehicle development costs (subset of ApolloSpending).

    Narrows the full Apollo spending sheet to the Saturn launch vehicle columns
    only, using the same CSV source and row-skip logic as ``ApolloSpending``.
    """

    COLUMNS: ClassVar[list[str]] = [
        "Fiscal Year",
        "Saturn Launch Vehicles",
        "Saturn C-I/I",
        "Saturn IB",
        "Saturn V",
        "Engine Development",
        "Support, Development, & Operations",
    ]

    MONETARY_COLUMNS: ClassVar[list[str]] = [
        "Saturn Launch Vehicles",
        "Saturn C-I/I",
        "Saturn IB",
        "Saturn V",
        "Engine Development",
        "Support, Development, & Operations",
    ]
