"""
inflation.py
============

Generic framework for fiscal-year inflation adjustments plus a concrete
NASA New-Start Index (NNSI) implementation.

---------------------------------------------------------------------------
Example
---------------------------------------------------------------------------
>>> nnsi = NNSI(year="2025")   # target FY 2025
>>> nnsi.calc("2014", 10)      # 10 → 13.59   (multiplied by 1.359)

"""

from __future__ import annotations
import io
import numpy as np
from pathlib import Path
from typing import Any, Mapping
import os, json
from collections import defaultdict
from datetime import datetime
import requests, certifi, pandas as pd


# ────────────────────────────── Base class ──────────────────────────────────
class Inflation:
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
    calc(from_year: str, value: float) -> float
        Return *value* adjusted from *from_year* → *self.year*.
    """

    def __init__(self, *, year: str, source: str | Path | None = None) -> None:
        self.year: str = year
        self.source: str | Path | None = source
        self._table: Mapping[str, float] = self._load_table()

    # ------------------------------------------------------------------ #
    #  Sub-classes *must* implement the following three hooks            #
    # ------------------------------------------------------------------ #
    def _load_raw(self) -> pd.DataFrame:
        """Return the raw price-index table as a DataFrame (no parsing)."""
        raise NotImplementedError

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
    def calc(self, from_year: str, value: float) -> float:
        """
        Multiply *value* by the correct factor for *from_year*.
        Falls back to *identity* (multiplier == 1.0) if no entry exists.
        """
        mult = self._table.get(self._normalise_key(from_year), 1.0)
        return value * mult

    def inflation_adjustment_year(self) -> str:
        """
        Return the fiscal year for which this inflation adjustment is valid.
        """
        return str(self.year)

    # utility for friendly key names
    @staticmethod
    def _normalise_key(year: str) -> str:
        return str(year).strip().upper()


# ───────────────────────────── NNSI subclass ────────────────────────────────
class NNSI(Inflation):
    """
    NASA New-Start Index (NNSI) adjustment.

    * Handles the special **Transition Quarter** row (“FROM TQ”).
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
        if Path(path_or_url).is_file():
            return pd.read_csv(path_or_url, header=None)
        text = requests.get(path_or_url, timeout=30, verify=certifi.where()).text
        return pd.read_csv(io.StringIO(text), header=None)

    # ---------- step 2: parse into lookup dict --------------------------
    def _parse_table(self, df: pd.DataFrame) -> Mapping[str, float]:
        # Header row is the *second* row (index 1)
        df = pd.read_csv(io.StringIO(df.to_csv(index=False)), header=2)
        df = df.rename(columns={df.columns[0]: "FROM"}).set_index("FROM")

        # Convert percentage strings to actual numbers; non-percentage strings are returned as-is
        # Function to convert percentage string to float
        def percentage_to_float(perc_str):
            if isinstance(perc_str, str) and perc_str.endswith('%'):
                try:
                    return float(perc_str.replace('%', '')) / 100
                except ValueError:
                    return np.nan
            return perc_str # Return the original value if it's not a percentage string
        
        df = df.applymap(percentage_to_float)
        
        # Remove any rows with only NaN values
        df = df.dropna(how="all")
        
        # Ensure numeric columns are ints where possible
        
        df.columns = [
            int(c) if str(c).isdigit() else c for c in df.columns
        ]
        target_col = int(self.year)  # will raise ValueError if not 4-digit
        if target_col not in df.columns:
            raise ValueError(f"NNSI table has no column for FY {self.year}")

        # Produce mapping; normalise keys (“FROM 2014”, “FROM TQ”) → FY string
        mapping: dict[str, float] = {}
        col = df[target_col]

        for idx, mult in col.items():
            key = idx.replace("FROM ", "").upper().strip()
            mapping[key] = float(mult)

        # also map plain year → multiplier (e.g. "2014": 1.359)
        mapping.update({k.lstrip("FROM ").strip(): v for k, v in mapping.items()})

        # special alias for Transition Quarter 1976
        mapping["1976 TQ"] = mapping.get("TQ", 1.0)

        return mapping

    # ---------- override only if key needs extra handling --------------
    def _normalise_key(self, year: str) -> str:
        s = super()._normalise_key(year)
        return "TQ" if s.endswith("TQ") or s == "TQ" else s



class GDP(Inflation):
    """
    Inflation adjuster using BEA's *implicit GDP price deflator, annual*.

    Priority of data sources
    ------------------------
    1. BEA API  - dataset=NIPA, TableName=T10109, LineNumber=1, Frequency=A
       • Requires an environment variable ``BEA_API_KEY``.
    2. FRED CSV - series ``GDPDEF`` (quarterly); this class auto-averages
       quarterly data into fiscal years.

    Examples
    --------
    >>> gdp = GDP(year="2024")          # target FY 2024
    >>> gdp.calc("2013", 25)            # => adjusted 2024 dollars
    """

    # ---------- raw BEA request helpers ---------------------------------
    _BEA_ENDPOINT = (
        "https://apps.bea.gov/api/data?"
        "UserID={key}&"
        "datasetname=NIPA&"
        "TableName=T10109&"      # Table 1.1.9 Implicit Price Deflators
        "LineNumber=1&"          # Line 1: Gross domestic product
        "Frequency=A&"           # Annual
        "Year=ALL&"
        "ResultFormat=JSON"
    )

    # FRED quarterly CSV (public, no key)
    _FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPDEF"

    # ---------- hook #1 --------------------------------------------------
    def _load_raw(self) -> pd.DataFrame:
        key = os.getenv("BEA_API_KEY")
        if key:                      # try BEA first
            url = self._BEA_ENDPOINT.format(key=key)
            resp = requests.get(url, timeout=30, verify=certifi.where())
            resp.raise_for_status()
            data = json.loads(resp.text)["BEAAPI"]["Results"]["Data"]
            return pd.DataFrame(data)
        # --- fall back to FRED ------------------------------------------
        csv = requests.get(self._FRED_CSV, timeout=30, verify=certifi.where()).text
        return pd.read_csv(io.StringIO(csv))

    # ---------- hook #2 --------------------------------------------------
    def _parse_table(self, df: pd.DataFrame) -> Mapping[str, float]:
        """
        Return { 'YYYY' -> multiplier } where multiplier =
        deflator[target_year] / deflator[from_year]
        """
        target = int(self.year)

        def _annualize(series, date_key="DATE", value_key="VALUE"):
            # Average quarterly values into fiscal years (Oct-Sep)
            q = (
                pd.to_datetime(series[date_key])
                .dt.to_period("Q")
                .dt.to_timestamp(freq="Q")
            )
            series = series.assign(FY=q.apply(lambda d: d.year if d.quarter == 4 else d.year - 1))
            return series.groupby("FY")[value_key].mean()

        # ---------- Parse depending on source shape ---------------------
        if {"LineDescription", "TimePeriod", "DataValue"}.issubset(df.columns):
            # BEA JSON -> tidy
            df = df.rename(columns={"TimePeriod": "FY", "DataValue": "VALUE"})
            df["FY"] = df["FY"].astype(int)
            df["VALUE"] = df["VALUE"].astype(float)
            annual = df.set_index("FY")["VALUE"]
        else:  # FRED CSV
            
            num_col = "GDPDEF"
            
            df = df[~df[num_col].isin([".", ""])]           # remove blanks
            df[num_col] = df[num_col].astype(float)
            # convert quarterly dates → fiscal-year averages (Oct--Sep)
            q_dates = pd.to_datetime(df["observation_date"]).dt.to_period("Q").dt.to_timestamp("Q")
            df = df.assign(FY=q_dates.apply(lambda d: d.year if d.quarter == 4 else d.year - 1))

            annual = df.groupby("FY")[num_col].mean()

        if target not in annual.index:
            raise ValueError(f"GDP deflator table lacks FY {target}")

        tgt_val = annual.loc[target]
        multipliers = (tgt_val / annual).to_dict()

        # Normalise keys to str so they match Inflation.calc inputs
        return {str(k): float(v) for k, v in multipliers.items()}