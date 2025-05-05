"""
nasa_budget.py  •  v2.1
=======================

• Adds automatic **inflation-adjusted columns** to the stored DataFrame:
    <monetary_col>_adjusted_nnsi   (NASA New-Start Index)
    <monetary_col>_adjusted_gdp    (GDP deflator - stub today)

  The adjustment is to *current fiscal year* at load-time.  
  Custom-year projections remain available through the dynamic
  `<col>_adjusted(type=…, year=…)` accessors.

• “1976 TQ” continues to map to the “FROM TQ” row of the NNSI table.

Only the base-class changes; concrete subclasses are unaffected.
"""
from __future__ import annotations

import io
import re
import ssl
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import Callable, List

import certifi
import pandas as pd
import requests
from urllib.error import URLError


# ─────────────────────────────────────────────────────────────────────────────
class NASABudget:
    _CURRENCY_RE = re.compile(r"[\$,]|\s*[MB]$", flags=re.IGNORECASE)

    # ─────────────────────────── constructor / cache ────────────────────────
    def __init__(self, csv_source: str | Path, *, cache_dir: Path | None = None) -> None:
        self._csv_source = str(csv_source)
        self._cache_dir = cache_dir

    # ───────────────────── public minimal interface ─────────────────────────
    def data(self) -> pd.DataFrame:
        """Return a deep copy of the cleaned & augmented DataFrame."""
        return self._df.copy(deep=True)

    def columns(self) -> List[str]:
        return list(self._df.columns)

    # Attribute access for arbitrary columns
    def __getattr__(self, name: str):
        if name in self._df.columns:
            return self._df[name].tolist()
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")

    # ─────────────────────────── convenience I/O ────────────────────────────
    def to_csv(self, path: str | Path, **kwargs) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._df.to_csv(path, index=False, **kwargs)
        return path

    def to_json(self, path_or_buf, orient: str = "records", **kwargs):
        return self._df.to_json(path_or_buf, orient=orient, **kwargs)

    # ─────────────────────────── time-series helpers ─────────────────────────
    def fy_range(self, start: int | None = None, end: int | None = None) -> pd.DataFrame:
        fy = self._fy_col()
        m = pd.Series(True, index=self._df.index)
        if start is not None:
            m &= self._df[fy] >= start
        if end is not None:
            m &= self._df[fy] <= end
        return self._df[m].copy()

    def percent_change(self, col: str, periods: int = 1) -> pd.Series:
        return self._df[col].pct_change(periods)

    def cagr(self, col: str, start_fy: int, end_fy: int) -> float:
        fy = self._fy_col()
        a = self._df.loc[self._df[fy] == start_fy, col].squeeze()
        b = self._df.loc[self._df[fy] == end_fy, col].squeeze()
        yrs = end_fy - start_fy
        if pd.isna(a) or pd.isna(b) or yrs <= 0:
            return float("nan")
        return (b / a) ** (1 / yrs) - 1

    def total_by_year(self, value_cols: list[str] | None = None) -> pd.Series:
        fy = self._fy_col()
        if value_cols is None:
            value_cols = self._df.select_dtypes("number").columns.tolist()
        return (
            self._df.groupby(fy)[value_cols]
            .sum(min_count=1)
            .sum(axis=1, min_count=1)
        )

    def pivot(self, *, index: str, columns: str, values: str) -> pd.DataFrame:
        return self._df.pivot(index=index, columns=columns, values=values)

    # ───────────────────────── diagnostics / QA ─────────────────────────────
    def info(self) -> None:
        print(f"=== {type(self).__name__}  •  source: {self._csv_source}\n")
        self._df.info()

    def missing(self, threshold: float = 0.10) -> pd.Series:
        frac = self._df.isna().mean()
        return frac[frac > threshold].sort_values(ascending=False)

    # Column filter
    def filter(self, columns: list[str]) -> pd.DataFrame:
        return self._df[columns].copy()

    # ────────────── auto-generated raw & adjusted property makers ───────────
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        monetary = getattr(cls, "MONETARY_COLUMNS", [])
        if not monetary:
            return

        def to_attr(col: str) -> str:
            return re.sub(r"\W+", "_", col).lower()

        for col in monetary:
            raw_attr = to_attr(col)
            if raw_attr not in cls.__dict__:
                setattr(cls, raw_attr, cls._make_raw_getter(col))

            adj_attr = f"{raw_attr}_adjusted"
            if adj_attr not in cls.__dict__:
                setattr(cls, adj_attr, cls._make_adjusted_getter(col))

    @classmethod
    def _make_raw_getter(cls, col: str) -> Callable[["NASABudget"], List[float]]:
        def _g(self: "NASABudget") -> List[float]:
            return self._df[col].tolist()

        _g.__doc__ = f"Raw nominal values from '{col}'."
        return _g

    @classmethod
    def _make_adjusted_getter(cls, col: str) -> Callable:
        def _g(
            self: "NASABudget", *, type: str = "nnsi", year: int | None = None
        ) -> List[float]:
            fy = self._fy_col()
            tgt = year if year is not None else self._current_fy()
            fn = (
                self._nnsi_multiplier
                if type.lower() == "nnsi"
                else self._gdp_multiplier
            )
            mult = self._df[fy].apply(lambda v: fn(v, tgt))
            return (self._df[col] * mult).tolist()

        _g.__doc__ = (
            f"'{col}' adjusted to *year* (default current FY) "
            "using NNSI (default) or GDP deflator."
        )
        return _g

    # ──────────────────────── DataFrame construction ────────────────────────
    @cached_property
    def _df(self) -> pd.DataFrame:
        raw = self._read_csv()

        # 1) optional subset
        subset = getattr(self.__class__, "COLUMNS", None)
        if subset:
            missing = set(subset) - set(raw.columns)
            if missing:
                raise KeyError(f"{type(self).__name__}: missing columns {missing}")
            raw = raw[subset].copy()

        # 2) optional rename
        ren = getattr(self.__class__, "RENAMES", None)
        if ren:
            miss = set(ren) - set(raw.columns)
            if miss:
                raise KeyError(f"{type(self).__name__}: cannot rename {miss}")
            raw = raw.rename(columns=ren)

        # 3) clean fields
        cleaned = self._clean(raw)

        # 4) add inflation-adjusted columns
        augmented = self._add_adjusted_columns(cleaned)

        return augmented

    # ------------------------------------------------------------------ #
    # CSV loader with cert fallback                                      #
    # ------------------------------------------------------------------ #
    def _read_csv(self) -> pd.DataFrame:
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            dest = self._cache_dir / Path(self._csv_source).name
            if dest.exists():
                return pd.read_csv(dest)

        try:
            df = pd.read_csv(self._csv_source)
        except (URLError, ssl.SSLError):
            resp = requests.get(self._csv_source, timeout=30, verify=certifi.where())
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))

        if self._cache_dir:
            (self._cache_dir / Path(self._csv_source).name).write_bytes(
                df.to_csv(index=False).encode()
            )
        return df

    # ------------------------------------------------------------------ #
    # cleaning helpers                                                   #
    # ------------------------------------------------------------------ #
    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # currency columns
        for col in df.select_dtypes("object"):
            if df[col].astype(str).str.contains(r"\$", na=False).any():
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(self._CURRENCY_RE, "", regex=True)
                    .astype(float, errors="ignore")
                    .mul(1_000_000)
                    .astype("Float64")
                )

        # date-style
        for col in df.columns:
            if re.search(r"(date|signed|updated)$", str(col), flags=re.I):
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

        # FY / year column – preserve 1976 TQ
        def norm(y):
            if pd.isna(y):
                return pd.NA
            s = str(y).strip()
            if "TQ" in s.upper():
                return "1976 TQ"
            if re.fullmatch(r"\d{4}", s):
                return int(s)
            return pd.NA

        for col in df.columns:
            if re.fullmatch(r"FY\d{2,4}", str(col), flags=re.I) or str(col).lower() in {
                "fiscal year",
                "fy",
                "year",
            }:
                df[col] = df[col].apply(norm)

        return df

    # ------------------------------------------------------------------ #
    # add _adjusted_nnsi / _adjusted_gdp columns                         #
    # ------------------------------------------------------------------ #
    def _add_adjusted_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        fy_col = self._fy_col()
        tgt = self._current_fy()
        mon = getattr(self.__class__, "MONETARY_COLUMNS", [])

        if not mon:
            return df

        nnsi_mult = df[fy_col].apply(lambda v: self._nnsi_multiplier(v, tgt))
        gdp_mult = df[fy_col].apply(lambda v: self._gdp_multiplier(v, tgt))

        for col in mon:
            if col not in df.columns:
                continue
            df[f"{col}_adjusted_nnsi"] = (df[col] * nnsi_mult).astype("Float64")
            df[f"{col}_adjusted_gdp"] = (df[col] * gdp_mult).astype("Float64")

        return df

    # ------------------------------------------------------------------ #
    # FY helpers                                                         #
    # ------------------------------------------------------------------ #
    def _fy_col(self) -> str:
        for c in self._df.columns:
            if re.fullmatch(r"FY\d{2,4}", str(c), flags=re.I) or str(c).lower() in {
                "fiscal year",
                "fy",
                "year",
            }:
                return c
        raise ValueError("No fiscal-year column found.")

    @staticmethod
    def _current_fy() -> int:
        today = date.today()
        return today.year + (today.month >= 10)

    # ──────────────────────────── inflation utils ───────────────────────────
    @cached_property
    def _nnsi_table(self) -> pd.DataFrame:
        url = (
            "https://docs.google.com/spreadsheets/d/"
            "1t7hYjU6AIAovar5sqi7cHXPmkWu6uAujsptMtGukQrA/export?format=csv"
        )
        r = requests.get(url, timeout=30, verify=certifi.where())
        r.raise_for_status()
        t = pd.read_csv(io.StringIO(r.text), header=1).rename(
            columns=lambda x: "FROM" if "Year" in str(x) else x
        )
        t = t.set_index("FROM")
        t.columns = [int(c) if re.fullmatch(r"\d{4}", str(c)) else c for c in t.columns]
        return t

    def _nnsi_multiplier(self, from_val, to_year: int) -> float:
        if pd.isna(from_val):
            return 1.0
        key = "FROM TQ" if isinstance(from_val, str) and "TQ" in from_val.upper() else f"FROM {int(from_val)}"
        try:
            return float(self._nnsi_table.loc[key, to_year])
        except KeyError:
            return 1.0

    # GDP deflator stub ---------------------------------------------------
    @cached_property
    def _gdp_deflator(self) -> pd.Series:
        return pd.Series(dtype=float)

    def _gdp_multiplier(self, from_val, to_year: int) -> float:
        return 1.0  # until implemented


# ───────────────────────────── concrete sheets ──────────────────────────────
class Historical(NASABudget):
    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=670209929"
    )
    COLUMNS = [
        "Year",
        "White House Budget Submission",
        "Appropriation",
        "Outlays",
        "% of U.S. Spending",
        "% of U.S. Discretionary Spending",
    ]
    RENAMES = {"Year": "Fiscal Year", "White House Budget Submission": "PBR"}
    MONETARY_COLUMNS = ["PBR", "Appropriation", "Outlays"]

    def __init__(self, *, cache_dir: Path | None = None) -> None:
        super().__init__(self.CSV_URL, cache_dir=cache_dir)


class Science(NASABudget):
    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=36975677"
    )
    # Define COLUMNS/RENAMES/MONETARY_COLUMNS as needed
    def __init__(self, *, cache_dir: Path | None = None) -> None:
        super().__init__(self.CSV_URL, cache_dir=cache_dir)


class Directorates(NASABudget):
    CSV_URL = (
        "https://docs.google.com/spreadsheets/d/"
        "1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export"
        "?format=csv&gid=1870113890"
    )
    def __init__(self, *, cache_dir: Path | None = None) -> None:
        super().__init__(self.CSV_URL, cache_dir=cache_dir)


# ───────────────────────── optional quick-test ──────────────────────────────
if __name__ == "__main__":
    h = Historical(cache_dir=Path(".cache"))
    print(h.columns()[:8])
    print(h.data().head()[["Fiscal Year", "Appropriation", "Appropriation_adjusted_nnsi"]])