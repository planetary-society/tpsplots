"""Tests for PlanetaryBudgetDataSource using the Cassini fixture."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource
from tpsplots.data_sources.planetary_budget_data_source import PlanetaryBudgetDataSource


@pytest.fixture()
def fixture_csv_text() -> str:
    return Path("tests/fixtures/planetary_cassini.csv").read_text()


@pytest.fixture()
def mock_fetch_csv(monkeypatch, fixture_csv_text):
    monkeypatch.setattr(
        GoogleSheetsSource,
        "_fetch_csv_content",
        staticmethod(lambda _url: fixture_csv_text),
    )


# ── Tab resolution ──


class TestTabResolution:
    def test_exact_tab_name(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("Cassini") == "Cassini"

    def test_integer_fiscal_year(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name(2026) == "FY 2026"

    def test_string_fiscal_year(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("2026") == "FY 2026"

    def test_case_insensitive(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("cassini") == "Cassini"
        assert PlanetaryBudgetDataSource._resolve_tab_name("fy 2026") == "FY 2026"

    def test_alias_fy1997(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("FY1997") == "FY 1997"

    def test_alias_msr(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("MSR") == "Mars Sample Return"

    def test_alias_case_insensitive(self):
        assert PlanetaryBudgetDataSource._resolve_tab_name("msr") == "Mars Sample Return"

    def test_invalid_tab_raises(self):
        with pytest.raises(ValueError, match="not available"):
            PlanetaryBudgetDataSource._resolve_tab_name("NonexistentTab")

    def test_available_tabs_returns_sorted_list(self):
        tabs = PlanetaryBudgetDataSource.available_tabs()
        assert isinstance(tabs, list)
        assert len(tabs) == len(PlanetaryBudgetDataSource.TAB_GID_LOOKUP)
        assert tabs == sorted(tabs)


# ── URL construction ──


def test_url_has_csv_format_and_correct_gid(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini")
    parsed = urlparse(source._url)
    query = parse_qs(parsed.query)
    assert query["format"] == ["csv"]
    assert query["gid"] == ["526464041"]


# ── Column handling ──


def test_first_column_not_renamed_when_named(mock_fetch_csv):
    """Cassini's first column is 'Official LCC', not unnamed — should stay."""
    source = PlanetaryBudgetDataSource("Cassini")
    df = source.data()
    assert df.columns[0] == "Official LCC"


# ── Monetary processing ──


def test_monetary_columns_are_numeric(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini")
    df = source.data()
    for col in ["Spacecraft Development", "Total Cost"]:
        assert pd.api.types.is_numeric_dtype(df[col])


def test_millions_to_absolute_applied(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini")
    df = source.data()
    # First data row: Spacecraft Development = $29.5M → 29,500,000
    assert df.iloc[0]["Spacecraft Development"] == pytest.approx(29_500_000)


def test_convert_millions_false_keeps_millions(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini", convert_millions=False)
    df = source.data()
    assert df.iloc[0]["Spacecraft Development"] == pytest.approx(29.5)


def test_data_not_double_scaled(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini")
    df_first = source.data()
    df_second = source.data()
    assert df_first["Total Cost"].iloc[0] == df_second["Total Cost"].iloc[0]


# ── Total row removal ──


def test_totals_row_removed(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini", convert_millions=False)
    df = source.data()
    first_col = df.columns[0]
    first_col_vals = df[first_col].astype(str).str.strip().str.lower()
    assert "totals" not in first_col_vals.values
    assert "total" not in first_col_vals.values


def test_trailing_rows_after_totals_removed(mock_fetch_csv):
    """The fixture has a '%' summary row after Totals — it should be gone."""
    source = PlanetaryBudgetDataSource("Cassini", convert_millions=False)
    df = source.data()
    # Fixture has 8 data rows before the Totals row
    assert len(df) == 8


# ── Properties ──


def test_tab_name_property(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("cassini")
    assert source.tab_name == "Cassini"


# ── Non-monetary column exclusions ──


def test_notes_column_not_treated_as_monetary(mock_fetch_csv):
    source = PlanetaryBudgetDataSource("Cassini")
    df = source.data()
    assert df["Notes"].dtype == object


def test_official_lcc_not_scaled(mock_fetch_csv):
    """Official LCC is excluded from monetary detection — should stay as-is."""
    source = PlanetaryBudgetDataSource("Cassini", convert_millions=False)
    df = source.data()
    # Official LCC is in _NON_MONETARY_PATTERNS, but it's also the first column
    # (excluded by default). Either way, it should not be numeric-converted.
    assert not pd.api.types.is_float_dtype(df["Official LCC"])
