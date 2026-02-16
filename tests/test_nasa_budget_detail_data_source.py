"""Tests for NASABudgetDetailSource using the FY2026 fixture."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.data_sources.nasa_budget_detail_data_source import NASABudgetDetailSource


@pytest.fixture()
def fixture_csv_text() -> str:
    return Path("tests/fixtures/nasa_fy2026.csv").read_text()


@pytest.fixture()
def mock_fetch_csv(monkeypatch, fixture_csv_text):
    monkeypatch.setattr(
        GoogleSheetsSource,
        "_fetch_csv_content",
        staticmethod(lambda _url: fixture_csv_text),
    )


def test_url_has_csv_format_and_gid_for_requested_fy(mock_fetch_csv):
    fy = 2026
    source = NASABudgetDetailSource(fy)
    parsed = urlparse(source._url)
    query = parse_qs(parsed.query)

    assert source._url.startswith(NASABudgetDetailSource.URL)
    assert query["format"] == ["csv"]
    assert query["gid"] == [NASABudgetDetailSource.NASA_FY_GOOGLE_SHEET_GID_LOOKUP[fy]]


def test_account_column_normalized(mock_fetch_csv):
    source = NASABudgetDetailSource(2026)
    df = source.data()
    assert df.columns[0] == "Account"


def test_monetary_columns_cleaned_and_scaled(mock_fetch_csv):
    source = NASABudgetDetailSource(2026)
    df = source.data()
    total_row = df.loc[df["Account"] == "Total"].iloc[0]

    assert pd.api.types.is_numeric_dtype(df["FY 2026 Request"])
    assert total_row["FY 2026 Request"] == pytest.approx(18_809_100_000)


def test_data_not_double_scaled(mock_fetch_csv):
    source = NASABudgetDetailSource(2026)
    df_first = source.data()
    df_second = source.data()
    total_first = df_first.loc[df_first["Account"] == "Total"].iloc[0]
    total_second = df_second.loc[df_second["Account"] == "Total"].iloc[0]

    assert total_first["FY 2026 Request"] == total_second["FY 2026 Request"]


def test_invalid_fy_raises():
    with pytest.raises(ValueError):
        NASABudgetDetailSource(2018)
