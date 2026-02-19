"""Data source for the Planetary Exploration Budget Dataset Google Sheet."""

from __future__ import annotations

import re
from typing import ClassVar

import pandas as pd

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource


class PlanetaryBudgetDataSource(GoogleSheetsSource):
    """Data source for The Planetary Society's Planetary Exploration Budget Dataset.

    Provides access to any of the 135 tabs in the spreadsheet by name, with
    automatic monetary column cleaning and millions-to-absolute conversion.

    Usage::

        source = PlanetaryBudgetDataSource("Cassini")
        df = source.data()

        source = PlanetaryBudgetDataSource(2026)  # shorthand for "FY 2026"
        df = source.data()

        source = PlanetaryBudgetDataSource("Cassini", convert_millions=False)
        df = source.data()  # values remain in millions
    """

    SPREADSHEET_ID: ClassVar[str] = "12frTU01gfT1CXGWFimN3whf4348F_r3XolTqBt02OyM"

    URL: ClassVar[str] = (
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"
    )

    # Disable base class auto-cleaning to avoid unwanted _raw columns;
    # we handle monetary cleaning ourselves in _clean_monetary_columns.
    AUTO_CLEAN_CURRENCY: ClassVar[bool] = False

    # Complete mapping of every tab name to its Google Sheets GID.
    TAB_GID_LOOKUP: ClassVar[dict[str, str]] = {
        # ── Metadata ──
        "Introduction": "1106105210",
        "Charts": "1644339331",
        # ── Aggregate data ──
        "Mission Costs": "1130871780",
        "Timeline": "565443030",
        "Planetary Science Budget History": "0",
        "Budget History (inflation adj)": "2130426444",
        "Funding by Destination": "1723911035",
        "Decadal Totals (inflation adj)": "81121468",
        "Major Programs, 1994 - current": "880601523",
        "Major Programs, 1960 - 1980": "167388071",
        # ── Missions ──
        "Cassini": "526464041",
        "CONTOUR": "327485694",
        "DART": "941152247",
        "DAVINCI": "9318267",
        "Dawn": "581649708",
        "Deep Impact": "497374677",
        "Deep Space 1": "1115062984",
        "Discovery Program": "1173725077",
        "Dragonfly": "677262513",
        "Europa Clipper": "1321332469",
        "Galileo": "760240834",
        "Genesis": "82407541",
        "GRAIL": "517216243",
        "Juno": "1282258103",
        "InSight": "736536820",
        "LADEE": "1362053641",
        "Lucy": "852099887",
        "Lunar Orbiters": "677761274",
        "Lunar Prospector": "35215052",
        "Magellan": "2134734096",
        "Mariner 10": "1871500702",
        "Mariner 8 & 9": "1785460489",
        "Mariner Program": "1863270757",
        "Mars Perseverance": "431387759",
        "Mars Global Surveyor": "680323465",
        "Mars Observer": "1416414350",
        "Mars Odyssey": "1484264283",
        "Mars Pathfinder": "1687800329",
        "MAVEN": "1774841387",
        "Mars Sample Return": "1083655313",
        "MESSENGER": "892109271",
        "MER": "1383585926",
        "MPL/MCO": "558084674",
        "MRO": "244635107",
        "MSL Curiosity": "1046473208",
        "NEAR": "1397610171",
        "NEO Surveyor": "1222549291",
        "New Horizons": "528701378",
        "OSIRIS-REx": "857538289",
        "Phoenix": "105787084",
        "Pioneer 10 & 11": "1456945880",
        "Pioneer Venus": "268004993",
        "Pioneer Program": "1571044441",
        "Planetary Defense": "330932421",
        "Psyche": "1098501409",
        "Ranger": "1767767204",
        "SIMPLEx Program": "1654991641",
        "Stardust": "1334282951",
        "Surveyor Program": "684395853",
        "VERITAS": "1965005977",
        "Viking": "1519124231",
        "VIPER": "541319818",
        "Voyager": "136534874",
        # ── Fiscal Year tabs ──
        "FY 2026": "1791037974",
        "FY 2025": "1871617532",
        "FY 2024": "1268768777",
        "FY 2023": "582799619",
        "FY 2022": "833131465",
        "FY 2021": "547317903",
        "FY 2020": "1881419405",
        "FY 2019": "995488773",
        "FY 2018": "1652311758",
        "FY 2017": "2107686770",
        "FY 2016": "1249458624",
        "FY 2015": "1103008440",
        "FY 2014": "95291420",
        "FY 2013": "847498988",
        "FY 2012": "1935709165",
        "FY 2011": "369060390",
        "FY 2010": "607257221",
        "FY 2009": "309255368",
        "FY 2008": "1456928242",
        "FY 2007": "1614981193",
        "FY 2006": "75481189",
        "FY 2005": "186678602",
        "FY 2004": "1505249412",
        "FY 2003": "1830211932",
        "FY 2002": "2080960406",
        "FY 2001": "1128716278",
        "FY 2000": "1814192538",
        "FY 1999": "847392512",
        "FY 1998": "319979364",
        "FY 1997": "894905413",
        "FY 1996": "14614269",
        "FY 1995": "619279008",
        "FY 1994": "1372110397",
        "FY 1993": "1522958201",
        "FY 1992": "1909899670",
        "FY 1991": "1083004952",
        "FY 1990": "1517729919",
        "FY 1989": "1594720578",
        "FY 1988": "1661308629",
        "FY 1987": "1356343862",
        "FY 1986": "1146736717",
        "FY 1985": "176538356",
        "FY 1984": "656118138",
        "FY 1983": "282898659",
        "FY 1982": "672551259",
        "FY 1981": "620912872",
        "FY 1980": "636277484",
        "FY 1979": "1292801630",
        "FY 1978": "757376883",
        "FY 1977": "897587641",
        "FY 1976": "1934744390",
        "FY 1976 TQ": "20752255",
        "FY 1975": "1644308736",
        "FY 1974": "1375322279",
        "FY 1973": "1254046823",
        "FY 1972": "1433810990",
        "FY 1971": "742557741",
        "FY 1970": "110754436",
        "FY 1969": "2109811876",
        "FY 1968": "96986285",
        "FY 1967": "329423742",
        "FY 1966": "1811521677",
        "FY 1965": "1361022865",
        "FY 1964": "1145176862",
        "FY 1963": "738161217",
        "FY 1962": "2029054377",
        "FY 1961": "441811383",
        "FY 1960": "2025132588",
        "FY 1959": "1912109296",
        # ── Reference ──
        "NNSI": "2109877667",
        "NAICS": "1052614187",
        "US Spending & Outlays": "279666886",
    }

    # Aliases for common alternative names. Maps alias → canonical name.
    TAB_ALIASES: ClassVar[dict[str, str]] = {
        "FY1997": "FY 1997",
        "Budget History": "Planetary Science Budget History",
        "MSR": "Mars Sample Return",
        "Mars 2020": "Mars Perseverance",
        "Curiosity": "MSL Curiosity",
        "Opportunity": "MER",
        "Spirit": "MER",
        "Major Programs": "Major Programs, 1994 - current",
    }

    # Tabs that are metadata/non-data (skip post-processing)
    _METADATA_TABS: ClassVar[frozenset[str]] = frozenset({"Introduction", "Charts"})

    # Column name patterns that should never be treated as monetary
    _NON_MONETARY_PATTERNS: ClassVar[list[str]] = [
        "Notes",
        "Sources",
        "Fiscal Year",
        "Official LCC",
    ]

    def __init__(
        self,
        tab: str | int,
        *,
        convert_millions: bool = True,
    ):
        """Initialize for a specific tab.

        Args:
            tab: Tab name (str) or fiscal year (int). Integers are converted
                to ``"FY YYYY"`` format. Matching is case-insensitive with
                alias support.
            convert_millions: If True (default), multiply detected monetary
                columns by 1,000,000 to convert from millions to absolute
                dollars.

        Raises:
            ValueError: If the tab name is not found in the lookup.
        """
        self._convert_millions = convert_millions
        self._tab_name = self._resolve_tab_name(tab)
        gid = self.TAB_GID_LOOKUP[self._tab_name]
        google_sheets_url = f"{self.URL}&gid={gid}"
        super().__init__(url=google_sheets_url)

        if self._tab_name not in self._METADATA_TABS:
            df = self._df
            self._normalize_columns(df)
            self._clean_monetary_columns(df)
            self._remove_total_and_trailing_rows(df)
            if self._convert_millions:
                self._millions_to_absolute(df)

    @classmethod
    def _resolve_tab_name(cls, tab: str | int) -> str:
        """Resolve a tab identifier to its canonical name.

        Supports exact match, case-insensitive match, aliases, integer fiscal
        years (e.g. ``2026`` → ``"FY 2026"``), and bare year strings.

        Raises:
            ValueError: If the tab cannot be resolved.
        """
        if isinstance(tab, int):
            tab = f"FY {tab}"

        tab_str = str(tab).strip()

        # Exact match
        if tab_str in cls.TAB_GID_LOOKUP:
            return tab_str

        # Alias match (case-insensitive)
        lower_tab = tab_str.lower()
        for alias, canonical in cls.TAB_ALIASES.items():
            if alias.lower() == lower_tab:
                return canonical

        # Case-insensitive match against canonical names
        lower_lookup = {name.lower(): name for name in cls.TAB_GID_LOOKUP}
        if lower_tab in lower_lookup:
            return lower_lookup[lower_tab]

        # Bare 4-digit year → "FY XXXX"
        if re.match(r"^\d{4}$", tab_str):
            fy_name = f"FY {tab_str}"
            if fy_name in cls.TAB_GID_LOOKUP:
                return fy_name

        available = sorted(cls.TAB_GID_LOOKUP.keys())
        raise ValueError(f"Tab '{tab}' is not available. Available tabs: {available}")

    @classmethod
    def available_tabs(cls) -> list[str]:
        """Return sorted list of all available tab names."""
        return sorted(cls.TAB_GID_LOOKUP.keys())

    @property
    def tab_name(self) -> str:
        """The resolved canonical tab name."""
        return self._tab_name

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> None:
        """Rename unnamed first columns to 'Account' (in-place)."""
        if df.columns.size == 0:
            return
        first_col = df.columns[0]
        first_col_str = str(first_col).strip()
        if not first_col_str or first_col_str.lower().startswith("unnamed"):
            df.rename(columns={first_col: "Account"}, inplace=True)

    def _clean_monetary_columns(self, df: pd.DataFrame) -> None:
        """Strip non-numeric characters from monetary columns and convert to float (in-place)."""
        for col in self._detect_monetary_columns(df):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^\d.-]", "", regex=True),
                errors="coerce",
            )

    def _millions_to_absolute(self, df: pd.DataFrame) -> None:
        """Convert monetary values from millions to absolute dollars (in-place)."""
        for col in self._detect_monetary_columns(df):
            df[col] = df[col] * 1_000_000

    @classmethod
    def _detect_monetary_columns(cls, df: pd.DataFrame) -> list[str]:
        """Return column names that contain monetary values.

        Excludes the first column, notes/sources, fiscal year, Official LCC,
        and any column whose name contains ``%``.
        """
        if df.columns.size == 0:
            return []

        exclude = {df.columns[0]}
        for col in df.columns:
            col_lower = str(col).strip().lower()
            if any(pat.lower() in col_lower for pat in cls._NON_MONETARY_PATTERNS):
                exclude.add(col)
            if "%" in str(col):
                exclude.add(col)

        return [col for col in df.columns if col not in exclude]

    @staticmethod
    def _remove_total_and_trailing_rows(df: pd.DataFrame) -> None:
        """Truncate from the first Total/Totals row onward (in-place).

        Finds the first row where the first column matches "Total" or "Totals"
        (case-insensitive) and drops that row and everything after it.
        """
        if df.columns.size == 0 or df.empty:
            return

        first_col = df.columns[0]
        first_col_vals = df[first_col].astype(str).str.strip().str.lower()
        total_mask = first_col_vals.isin({"total", "totals"})
        total_indices = df.index[total_mask]

        if len(total_indices) > 0:
            first_total_idx = total_indices[0]
            rows_to_drop = df.loc[first_total_idx:].index
            df.drop(rows_to_drop, inplace=True)
