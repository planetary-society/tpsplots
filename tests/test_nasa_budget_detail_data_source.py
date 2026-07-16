"""Tests for NASABudgetDetailSource using the FY2026 fixture."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.data_sources.nasa_budget_detail_data_source import NASABudgetDetailSource
from tpsplots.utils.currency_processing import clean_currency_column


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


# ---------------------------------------------------------------------------
# Characterization tests for the detail source's currency cleaning.
#
# NASABudgetDetailSource._clean_monetary_columns strips every character except
# digits, ".", and "-" (regex ``[^\d.-]``) before to_numeric coercion, then
# _millions_to_absolute multiplies by 1e6. These tests lock in that CURRENT
# behavior so it cannot drift silently.
#
# The shared helper ``clean_currency_column`` is NOT a drop-in replacement: it
# only removes ``$``, ``,``, and a trailing M/B suffix, so it diverges on
# parenthesized negatives such as "(1,234)" (see the divergence test below).
# Do not consolidate onto the shared helper without changing behavior.
# ---------------------------------------------------------------------------


# input string -> expected value AFTER cleaning + millions-to-absolute scaling
_DETAIL_CLEANING_CASES = [
    ("$1,234.5", 1_234_500_000.0),
    ("1234", 1_234_000_000.0),
    ("(1,234)", 1_234_000_000.0),  # parens stripped -> becomes POSITIVE, not NaN
    ("-", None),
    ("", None),
    ("1.2B", 1_200_000.0),  # 'B' stripped, then scaled as millions
    ("1.2M", 1_200_000.0),  # 'M' stripped, then scaled as millions
    (None, None),
    ("N/A", None),
]


def _run_detail_cleaning(mock_fetch_csv, values):
    source = NASABudgetDetailSource(2026)
    df = pd.DataFrame({"Account": [f"row{i}" for i in range(len(values))], "Value": values})
    source._clean_monetary_columns(df)
    source._millions_to_absolute(df)
    return df["Value"]


@pytest.mark.parametrize(("raw", "expected"), _DETAIL_CLEANING_CASES)
def test_detail_monetary_cleaning_characterization(mock_fetch_csv, raw, expected):
    result = _run_detail_cleaning(mock_fetch_csv, [raw]).iloc[0]
    if expected is None:
        assert pd.isna(result)
    else:
        assert result == pytest.approx(expected)


def test_detail_cleaning_diverges_from_shared_helper_on_parens(mock_fetch_csv):
    """Document the one input where the detail source and the shared helper differ.

    The detail source strips parentheses and returns a positive value, while
    clean_currency_column keeps them and coerces to NaN. All other
    representative inputs agree.
    """
    values = [raw for raw, _ in _DETAIL_CLEANING_CASES]
    detail = _run_detail_cleaning(mock_fetch_csv, values)
    canonical = clean_currency_column(pd.Series(values, dtype="object"), multiplier=1e6)

    disagreements = {
        raw
        for raw, d, c in zip(values, detail, canonical, strict=True)
        if not ((pd.isna(d) and pd.isna(c)) or d == c)
    }
    assert disagreements == {"(1,234)"}
