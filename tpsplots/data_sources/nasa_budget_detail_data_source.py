from typing import ClassVar

import pandas as pd

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource


class NASABudgetDetailSource(GoogleSheetsSource):
    """Data source for detailed NASA budget data from a Google Sheets URL."""

    # Base URL for budget detail sheet (gid appended per FY)
    URL: ClassVar[
        str
    ] = "https://docs.google.com/spreadsheets/d/1NMRYCCRWXwpn3pZU57-Bb0P1Zp3yg2lTTVUzvc5GkIs/export?format=csv"

    NASA_FY_GOOGLE_SHEET_GID_LOOKUP: ClassVar[dict[int, str]] = {
        2027: "1991531891",
        2026: "1311027224",
        2025: "976321042",
        2024: "333818355",
        2023: "1164738485",
        2022: "757486787",
        2021: "1531105314",
        2020: "1883310341",
        2019: "2070536405"
    }

    def __init__(self, fy: int):
        if fy not in self.NASA_FY_GOOGLE_SHEET_GID_LOOKUP:
            raise ValueError(
                f"Fiscal year {fy} is not supported. Available fiscal years: "
                f"{list(self.NASA_FY_GOOGLE_SHEET_GID_LOOKUP.keys())}"
            )
        gid = self.NASA_FY_GOOGLE_SHEET_GID_LOOKUP[fy]
        google_sheets_url = f"{self.URL}&gid={gid}"
        super().__init__(url=google_sheets_url)

        # Force load and normalize once; data() returns copies of this cached DataFrame
        df = self._df
        self._normalize_columns(df)
        self._clean_monetary_columns(df)
        self._millions_to_absolute(df)

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> None:
        """Normalize column names for consistency (in-place)."""
        if df.columns.size == 0:
            return
        # The FY detail sheet often has an unnamed first column for account names.
        first_col = df.columns[0]
        first_col_str = str(first_col).strip()
        if not first_col_str or first_col_str.lower().startswith("unnamed"):
            df.rename(columns={first_col: "Account"}, inplace=True)

    def _millions_to_absolute(self, df: pd.DataFrame) -> None:
        """Converts monetary values from millions to absolute values (in-place)."""
        monetary_columns = self._detect_monetary_columns(df)
        for col in monetary_columns:
            df[col] = df[col] * 1_000_000

    def _clean_monetary_columns(self, df: pd.DataFrame) -> None:
        """Cleans monetary columns by removing non-numeric characters and converting to float."""
        monetary_columns = self._detect_monetary_columns(df)
        for col in monetary_columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^\d.-]", "", regex=True),
                errors="coerce",
            )

    @staticmethod
    def _detect_monetary_columns(df: pd.DataFrame) -> list[str]:
        """Detect columns that contain monetary values for the FY detail sheet."""
        if df.columns.size == 0:
            return []

        account_col = df.columns[0]
        non_monetary = {account_col, "Notes"}
        return [col for col in df.columns if col not in non_monetary]
