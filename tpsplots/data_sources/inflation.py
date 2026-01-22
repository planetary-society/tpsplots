"""
inflation.py
============

Generic framework for fiscal-year inflation adjustments plus a concrete
NASA New-Start Index (NNSI) implementation.

---------------------------------------------------------------------------
Example
---------------------------------------------------------------------------
>>> nnsi = NNSI(year="2025")  # target FY 2025
>>> nnsi.calc("2014", 10)  # 10 → 13.59   (multiplied by 1.359)
>>> nnsi.calc(datetime(2014, 1, 1), 10)  # Also handles datetime objects

"""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

import certifi
import numpy as np
import pandas as pd
import requests

from tpsplots.exceptions import DataSourceError

logger = logging.getLogger(__name__)


# Base class
class Inflation(ABC):
    """
    Abstract inflation/price-level adjuster.

    Parameters
    ----------
    year:
        Target fiscal year **as a string** (e.g. ``"2025"``).  Sub-classes may
        accept special tokens like ``"2025 Q1"`` if relevant to their table.
    source:
        URL or local file path to the raw table.  Optional for sub-classes
        that hard-code their own endpoint.

    Public API
    ----------
    calc(from_year: Union[str, datetime, int], value: float) -> float
        Return *value* adjusted from *from_year* → *self.year*.
    """

    def __init__(self, *, year: str, source: str | Path | None = None) -> None:
        self.year: str = year
        self.source: str | Path | None = source
        self._table: Mapping[str, float] = self._load_table()
        if not self._table:
            raise DataSourceError(
                f"No inflation data available for {self.__class__.__name__} (year={self.year})"
            )

    # ------------------------------------------------------------------ #
    #  Sub-classes *must* implement the following three hooks            #
    # ------------------------------------------------------------------ #
    @abstractmethod
    def _load_raw(self) -> pd.DataFrame:
        """Return the raw price-index table as a DataFrame (no parsing)."""
        raise NotImplementedError

    @abstractmethod
    def _parse_table(self, df: pd.DataFrame) -> Mapping[str, float]:
        """
        Convert *df* into a mapping: ``{from_year_str -> multiplier(float)}``
        for the chosen **target** fiscal year (``self.year``).
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    #  Template method -- do not override in sub-classes                  #
    # ------------------------------------------------------------------ #
    def _load_table(self) -> Mapping[str, float]:
        raw = self._load_raw()
        return self._parse_table(raw)

    # ------------------------------------------------------------------ #
    #  Public helper                                                     #
    # ------------------------------------------------------------------ #
    def calc(self, from_year: str | datetime | int, value: float) -> float:
        """
        Multiply *value* by the correct factor for *from_year*.
        Falls back to *identity* (multiplier == 1.0) if no entry exists.

        Args:
            from_year: The fiscal year to adjust from, can be a string, datetime object, or integer.
            value: The value to adjust.

        Returns:
            float: The inflation-adjusted value.
        """
        key = self._convert_year_to_key(from_year)
        mult = self._table.get(self._normalise_key(key), 1.0)
        return value * mult

    def _convert_year_to_key(self, year_input: str | datetime | int) -> str:
        """
        Convert various year input formats to a standard string key format.

        Args:
            year_input: The year as a string, datetime object, or integer.

        Returns:
            str: The year as a standardized string.
        """
        if isinstance(year_input, datetime):
            return str(year_input.year)
        if isinstance(year_input, int):
            return str(year_input)
        if isinstance(year_input, str) and "TQ" in year_input.upper():
            return year_input
        return str(year_input)

    def inflation_adjustment_year(self) -> str:
        """
        Return the fiscal year for which this inflation adjustment is valid.
        """
        return str(self.year)

    # utility for friendly key names
    @staticmethod
    def _normalise_key(year: str) -> str:
        return str(year).strip().upper()


# NNSI subclass
class NNSI(Inflation):
    """
    NASA New-Start Index (NNSI) adjustment.

    * Handles the special **Transition Quarter** row ("FROM TQ").
    * Automatically downloads the latest Google-Sheets CSV unless a local
      path is provided.
    """

    # The NNSI table is provided by a Google Sheet maintained by Casey Dreier,
    # which is then exported as CSV. You could also reference the
    # The format retains the standard NNSI XLS table as produced by the NASA OCFO
    DEFAULT_CSV = (
        "https://docs.google.com/spreadsheets/d/"
        "1t7hYjU6AIAovar5sqi7cHXPmkWu6uAujsptMtGukQrA/export?format=csv"
    )

    # ---------- step 1: fetch raw file ----------------------------------
    def _load_raw(self) -> pd.DataFrame:
        path_or_url = self.source or self.DEFAULT_CSV
        return _read_csv_source(path_or_url, header=None)

    # ---------- step 2: parse into lookup dict --------------------------
    def _parse_table(self, df: pd.DataFrame) -> Mapping[str, float]:
        header_idx = self._find_header_row(df)
        columns = self._extract_columns(df.iloc[header_idx].tolist())
        data = df.iloc[header_idx + 1 :, : len(columns)].copy()
        data.columns = columns

        from_col = columns[0]
        data = data.rename(columns={from_col: "FROM"})
        data = data[
            data["FROM"].astype(str).str.upper().str.startswith("FROM")
        ]
        data = data.set_index("FROM")

        data = data.apply(lambda col: col.map(self._coerce_numeric))
        data = data.dropna(how="all")
        data.columns = [self._normalize_column(c) for c in data.columns]
        data = data.loc[:, [c for c in data.columns if c is not None]]

        target_col = int(self.year)
        if target_col not in data.columns:
            logger.warning(
                f"NNSI table has no column for FY {self.year}; inflation adjustment disabled"
            )
            return {}

        mapping: dict[str, float] = {}
        for idx, mult in data[target_col].dropna().items():
            key = self._strip_from_prefix(idx)
            mapping[key] = float(mult)

        mapping["1976 TQ"] = mapping.get("TQ", 1.0)
        return mapping

    @staticmethod
    def _find_header_row(df: pd.DataFrame) -> int:
        first_col = df.iloc[:, 0].astype(str).str.strip().str.upper()
        matches = first_col[first_col == "YEAR"]
        if matches.empty:
            raise DataSourceError("NNSI table header row not found.")
        return int(matches.index[0])

    @staticmethod
    def _extract_columns(values: list[object]) -> list[str]:
        columns = []
        for value in values:
            if value is None or (isinstance(value, float) and np.isnan(value)):
                break
            text = str(value).strip()
            if not text:
                break
            columns.append(text)
        if not columns:
            raise DataSourceError("NNSI table header row is empty.")
        return columns

    @staticmethod
    def _normalize_column(value: object) -> str | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        text = str(value).strip()
        if not text:
            return None
        if text.isdigit():
            return int(text)
        return text

    @staticmethod
    def _strip_from_prefix(value: object) -> str:
        text = str(value).strip()
        if text.upper().startswith("FROM"):
            text = text[4:]
        return text.strip().upper()

    @staticmethod
    def _coerce_numeric(value: object) -> float | None:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return np.nan
        text = str(value).strip()
        if not text:
            return np.nan
        if text.endswith("%"):
            text = text.rstrip("%").strip()
            try:
                return float(text) / 100
            except ValueError:
                return np.nan
        try:
            return float(text)
        except ValueError:
            return np.nan

    # ---------- override only if key needs extra handling --------------
    def _normalise_key(self, year: str) -> str:
        s = super()._normalise_key(year)
        return "TQ" if s.endswith("TQ") or s == "TQ" else s


class GDP(Inflation):
    """
    Inflation adjuster using FRED's GDP deflator (quarterly).

    This class auto-averages available quarters into fiscal years.

    Examples
    --------
    >>> gdp = GDP(year="2024")  # target FY 2024
    >>> gdp.calc("2013", 25)  # => adjusted 2024 dollars
    >>> gdp.calc(datetime(2013, 1, 1), 25)  # Same as above
    """

    # FRED quarterly CSV (public, no key)
    _FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPDEF"

    # ---------- hook #1 --------------------------------------------------
    def _load_raw(self) -> pd.DataFrame:
        return _read_csv_source(self._FRED_CSV)

    @staticmethod
    def _annualize_quarters(
        df: pd.DataFrame, date_col: str, value_col: str
    ) -> tuple[pd.Series, pd.Series]:
        """Average available quarters into fiscal-year values."""
        quarters = pd.to_datetime(df[date_col]).dt.to_period("Q")
        fiscal_years = quarters.dt.year + (quarters.dt.quarter == 4).astype(int)
        df = df.assign(FY=fiscal_years)
        annual = df.groupby("FY")[value_col].mean()
        quarter_counts = df.groupby("FY")[value_col].count()
        return annual, quarter_counts

    # ---------- hook #2 --------------------------------------------------
    def _parse_table(self, df: pd.DataFrame) -> Mapping[str, float]:
        """
        Return { 'YYYY' -> multiplier } where multiplier =
        deflator[target_year] / deflator[from_year]
        """
        target = int(self.year)

        num_col = "GDPDEF"

        df = df[~df[num_col].isin([".", ""])]  # remove blanks
        df[num_col] = df[num_col].astype(float)
        annual, quarter_counts = self._annualize_quarters(
            df,
            "observation_date",
            num_col,
        )
        if target in quarter_counts.index and quarter_counts.loc[target] < 4:
            logger.warning(
                f"GDP deflator FY {target} computed from {quarter_counts.loc[target]} quarters"
            )

        if target not in annual.index:
            logger.warning(f"GDP deflator table lacks FY {target}; inflation adjustment disabled")
            return {}

        tgt_val = annual.loc[target]
        multipliers = (tgt_val / annual).to_dict()

        # Normalise keys to str so they match Inflation.calc inputs
        return {str(k): float(v) for k, v in multipliers.items()}


def _read_csv_source(source: str | Path, header: int | None = 0) -> pd.DataFrame:
    path = Path(source)
    if path.is_file():
        return pd.read_csv(path, header=header)
    response = requests.get(str(source), timeout=30, verify=certifi.where())
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text), header=header)
