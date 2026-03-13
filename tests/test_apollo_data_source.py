"""Tests for Apollo-era data sources.

Tests focus on:
- Skipping the junk first row (category headers) — Apollo only
- Truncating at the "Totals" row — all sources
- Currency cleaning with 1,000 multiplier (thousands to dollars)
- Percentage column cleaning
- Fiscal year detection
- MONETARY_COLUMNS auto-getter generation
- RoboticLunarPrograms, ProjectGemini, FacilitiesConstruction
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Fixture CSV that mimics the real spreadsheet structure:
# Row 1: junk category header (merged cells become empty commas)
# Row 2: real column headers
# Rows 3-5: data rows
# Row 6: Totals row (should be truncated)
# Row 7+: trailing content (should be truncated)
FIXTURE_CSV = """\
,,,,Direct Project Costs,,,,Related Programs,,
Fiscal Year,NASA Total Obligations,Lunar effort % of NASA,Lunar Effort Total,Annual Direct Costs,Spacecraft,CSM,LM,Annual Related Programs Cost,Robotic Lunar Missions,Project Gemini
1960,"$487,000",4%,"$69,120","$57,420",$0,$0,$0,"$11,700","$11,700",$0
1961,"$908,300",39%,"$358,274","$181,094","$6,266",$0,$0,"$52,780","$52,780",$0
1962,"$1,691,600",57%,"$971,882","$484,582","$95,205","$60,000",$0,"$101,900","$101,900",$0
Totals,"$3,086,900",57%,"$1,399,276","$723,096","$101,471","$60,000",$0,"$166,380","$166,380",$0
,,,,,,,,,,
Total Project Apollo,"$25,774,138",,,,,,,,
,,,,,,,,,,
All values in thousands of dollars,,,,,,,,,,
"""


@pytest.fixture()
def mock_response():
    """Create a mock requests.Response returning the fixture CSV."""
    resp = MagicMock()
    resp.text = FIXTURE_CSV
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def apollo_instance(mock_response):
    """Create an Apollo instance with mocked network calls."""
    with patch("tpsplots.data_sources.apollo_data_source.requests.get", return_value=mock_response):
        from tpsplots.data_sources.apollo_data_source import ApolloSpending

        instance = ApolloSpending()
        # Force _df computation while mock is active
        _ = instance.data()
        yield instance


class TestApolloSkipFirstRow:
    """Row 1 (junk category header) is skipped; row 2 has real headers."""

    def test_columns_match_expected_headers(self, apollo_instance):
        """Column names should come from row 2, not the junk row 1."""
        df = apollo_instance.data()
        assert "Fiscal Year" in df.columns
        assert "NASA Total Obligations" in df.columns
        assert "CSM" in df.columns
        # Junk row values should NOT appear as column names
        assert "Direct Project Costs" not in df.columns
        assert "Related Programs" not in df.columns

    def test_no_junk_row_in_data(self, apollo_instance):
        """The junk category header row should not appear as data."""
        df = apollo_instance.data()
        first_col_vals = df["Fiscal Year"].astype(str).tolist()
        assert "Direct Project Costs" not in first_col_vals
        assert "" not in first_col_vals


class TestApolloTruncation:
    """The 'Totals' row and everything after it is removed."""

    def test_totals_row_excluded(self, apollo_instance):
        """The Totals row should not appear in the data."""
        df = apollo_instance.data()
        fy_vals = df["Fiscal Year"].astype(str).tolist()
        for val in fy_vals:
            assert "total" not in val.lower()

    def test_row_count(self, apollo_instance):
        """Only the 3 data rows (1960, 1961, 1962) should remain."""
        df = apollo_instance.data()
        assert len(df) == 3

    def test_trailing_rows_excluded(self, apollo_instance):
        """Rows after Totals (Total Project Apollo, notes) should not appear."""
        df = apollo_instance.data()
        all_vals = df.values.astype(str).flatten()
        assert not any("Total Project Apollo" in v for v in all_vals)
        assert not any("All values in thousands" in v for v in all_vals)


class TestApolloCurrencyMultiplier:
    """Currency values are multiplied by 1,000 (thousands to dollars)."""

    def test_currency_values_multiplied(self, apollo_instance):
        """$487,000 in source (thousands) should become 487_000_000 dollars."""
        df = apollo_instance.data()
        # First row: NASA Total Obligations = $487,000 (thousands)
        # After cleaning: 487000 * 1000 = 487_000_000
        first_val = df["NASA Total Obligations"].iloc[0]
        assert first_val == pytest.approx(487_000_000)

    def test_zero_values(self, apollo_instance):
        """$0 values should remain 0 after cleaning."""
        df = apollo_instance.data()
        # First row: CSM = $0
        assert df["CSM"].iloc[0] == pytest.approx(0.0)

    def test_monetary_columns_are_numeric(self, apollo_instance):
        """All monetary columns should be float64 after cleaning."""
        df = apollo_instance.data()
        for col in ["NASA Total Obligations", "Lunar Effort Total", "Spacecraft", "CSM"]:
            if col in df.columns:
                assert pd.api.types.is_float_dtype(df[col]), f"{col} should be float64"


class TestApolloPercentage:
    """Percentage column is cleaned to numeric values."""

    def test_percentage_cleaned(self, apollo_instance):
        """'4%' should become 4.0, '39%' should become 39.0."""
        df = apollo_instance.data()
        pct = df["Lunar effort % of NASA"]
        assert pct.iloc[0] == pytest.approx(4.0)
        assert pct.iloc[1] == pytest.approx(39.0)
        assert pct.iloc[2] == pytest.approx(57.0)

    def test_percentage_is_numeric(self, apollo_instance):
        """Percentage column should be numeric after cleaning."""
        df = apollo_instance.data()
        assert pd.api.types.is_numeric_dtype(df["Lunar effort % of NASA"])


class TestApolloFiscalYear:
    """Fiscal Year column is detected and converted to datetime."""

    def test_fiscal_year_detected(self, apollo_instance):
        """Fiscal Year column should be auto-detected."""
        df = apollo_instance.data()
        assert "Fiscal Year" in df.columns

    def test_fiscal_year_is_datetime(self, apollo_instance):
        """Fiscal Year should be converted to datetime."""
        df = apollo_instance.data()
        assert pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"])

    def test_fiscal_year_values(self, apollo_instance):
        """FY values should represent 1960, 1961, 1962."""
        df = apollo_instance.data()
        years = df["Fiscal Year"].dt.year.tolist()
        assert years == [1960, 1961, 1962]


class TestApolloAutoGetters:
    """MONETARY_COLUMNS generates auto-getter attributes via __init_subclass__."""

    def test_auto_getter_exists(self, apollo_instance):
        """Auto-getters like .csm() are callable and return lists."""
        assert callable(apollo_instance.csm)
        vals = apollo_instance.csm()
        assert isinstance(vals, list)
        assert len(vals) == 3

    def test_auto_getter_values(self, apollo_instance):
        """Auto-getter values should match cleaned DataFrame values."""
        df = apollo_instance.data()
        assert apollo_instance.csm() == df["CSM"].tolist()

    def test_spacecraft_getter(self, apollo_instance):
        """Spacecraft auto-getter should work."""
        vals = apollo_instance.spacecraft()
        assert isinstance(vals, list)


class TestApolloDataMethod:
    """The data() method returns a deep copy."""

    def test_data_returns_copy(self, apollo_instance):
        """Modifying returned DataFrame should not affect the source."""
        df1 = apollo_instance.data()
        df1["CSM"] = 0
        df2 = apollo_instance.data()
        assert not (df2["CSM"] == 0).all()

    def test_data_returns_dataframe(self, apollo_instance):
        """data() should return a pandas DataFrame."""
        df = apollo_instance.data()
        assert isinstance(df, pd.DataFrame)


class TestApolloClassAttributes:
    """Class-level attributes are correctly defined."""

    def test_monetary_columns_count(self):
        """All 25 monetary columns should be listed."""
        from tpsplots.data_sources.apollo_data_source import ApolloSpending

        assert len(ApolloSpending.MONETARY_COLUMNS) == 25

    def test_percentage_columns(self):
        """Percentage columns should list the lunar effort percentage."""
        from tpsplots.data_sources.apollo_data_source import ApolloSpending

        assert ApolloSpending.PERCENTAGE_COLUMNS == ["Lunar effort % of NASA"]

    def test_csv_url_format(self):
        """CSV URL should use ? not & for query string start."""
        from tpsplots.data_sources.apollo_data_source import ApolloSpending

        assert "export?format=csv" in ApolloSpending.CSV_URL
        assert "export&format=csv" not in ApolloSpending.CSV_URL


# ────────────────────────── Robotic Lunar Programs ──────────────────────────

ROBOTIC_LUNAR_CSV = """\
Year,Ranger,Surveyor,Lunar Orbiter,Total Robotic,Total (NNSI Inflation Adj),,
1959,"$3,400",$0,$0,"$3,400","$56,562",,all values in thousands of dollars
1960,"$11,700",$0,$0,"$11,700","$186,615",,Source: NASA Historical Data Book Vol 1
1961,"$52,300",$480,$0,"$52,780","$815,715",,
Totals,"$67,400",$480,$0,"$67,880","$1,058,892",,
"""


@pytest.fixture()
def robotic_lunar_instance():
    """Create a RoboticLunarPrograms instance with mocked network calls."""
    resp = MagicMock()
    resp.text = ROBOTIC_LUNAR_CSV
    resp.raise_for_status = MagicMock()
    with (
        patch("tpsplots.data_sources.apollo_data_source.requests.get", return_value=resp),
        patch(
            "tpsplots.data_sources.nasa_budget_data_source.NASABudget._fetch_url_content",
            return_value=ROBOTIC_LUNAR_CSV,
        ),
    ):
        from tpsplots.data_sources.apollo_data_source import RoboticLunarProgramSpending

        instance = RoboticLunarProgramSpending()
        _ = instance.data()
        yield instance


class TestRoboticLunarPrograms:
    """Tests for the Robotic Lunar Programs data source."""

    def test_no_skiprows_needed(self, robotic_lunar_instance):
        """First row is the real header — 'Year' should be a column."""
        df = robotic_lunar_instance.data()
        assert "Year" in df.columns

    def test_truncation(self, robotic_lunar_instance):
        """Totals row and trailing content are removed."""
        df = robotic_lunar_instance.data()
        assert len(df) == 3

    def test_columns_selected(self, robotic_lunar_instance):
        """Only COLUMNS-listed columns should be present (no trailing empties)."""
        df = robotic_lunar_instance.data()
        assert "Total Robotic" in df.columns
        # Pre-computed inflation column excluded by COLUMNS
        assert "Total (NNSI Inflation Adj)" not in df.columns

    def test_currency_multiplied(self, robotic_lunar_instance):
        """$3,400 (thousands) should become 3,400,000."""
        df = robotic_lunar_instance.data()
        assert df["Ranger"].iloc[0] == pytest.approx(3_400_000)

    def test_monetary_columns(self):
        from tpsplots.data_sources.apollo_data_source import RoboticLunarProgramSpending

        assert len(RoboticLunarProgramSpending.MONETARY_COLUMNS) == 4

    def test_fiscal_year_detected(self, robotic_lunar_instance):
        """'Year' column should be auto-detected as fiscal year."""
        df = robotic_lunar_instance.data()
        assert pd.api.types.is_datetime64_any_dtype(df["Year"])


# ────────────────────────── Project Gemini ──────────────────────────

GEMINI_CSV = """\
Fiscal Year,Spacecraft,Support,Launch Vehicle,Total,,
1962,"$30,600",$0,"$24,400","$55,000",,
1963,"$205,100","$3,400","$79,100","$287,600",,
Totals,"$235,700","$3,400","$103,500","$342,600",,
"""


@pytest.fixture()
def gemini_instance():
    """Create a ProjectGemini instance with mocked network calls."""
    resp = MagicMock()
    resp.text = GEMINI_CSV
    resp.raise_for_status = MagicMock()
    with patch(
        "tpsplots.data_sources.nasa_budget_data_source.NASABudget._fetch_url_content",
        return_value=GEMINI_CSV,
    ):
        from tpsplots.data_sources.apollo_data_source import ProjectGemini

        instance = ProjectGemini()
        _ = instance.data()
        yield instance


class TestProjectGemini:
    """Tests for the Project Gemini data source."""

    def test_truncation(self, gemini_instance):
        df = gemini_instance.data()
        assert len(df) == 2

    def test_columns_selected(self, gemini_instance):
        df = gemini_instance.data()
        assert "Spacecraft" in df.columns
        assert "Total" in df.columns

    def test_currency_multiplied(self, gemini_instance):
        """$30,600 (thousands) should become 30,600,000."""
        df = gemini_instance.data()
        assert df["Spacecraft"].iloc[0] == pytest.approx(30_600_000)

    def test_monetary_columns(self):
        from tpsplots.data_sources.apollo_data_source import ProjectGemini

        assert len(ProjectGemini.MONETARY_COLUMNS) == 4

    def test_fiscal_year_detected(self, gemini_instance):
        df = gemini_instance.data()
        assert pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"])


# ────────────────────────── Facilities Construction ──────────────────────────

FACILITIES_CSV = """\
Year,Manned Spaceflight Ground Facilities,Office of Tracking and Data Acquisition Facilities,Total Facilities,Total Facilities (PWC Inflation Adj)
1961,"$53,400",$0,"$53,400","$668,322"
1962,"$252,400",$0,"$252,400","$3,030,663"
Totals,"$305,800",$0,"$305,800","$3,698,985"
"""


@pytest.fixture()
def facilities_instance():
    """Create a FacilitiesConstruction instance with mocked network calls."""
    resp = MagicMock()
    resp.text = FACILITIES_CSV
    resp.raise_for_status = MagicMock()
    with patch(
        "tpsplots.data_sources.nasa_budget_data_source.NASABudget._fetch_url_content",
        return_value=FACILITIES_CSV,
    ):
        from tpsplots.data_sources.apollo_data_source import FacilitiesConstructionSpending

        instance = FacilitiesConstructionSpending()
        _ = instance.data()
        yield instance


class TestFacilitiesConstruction:
    """Tests for the Facilities Construction data source."""

    def test_truncation(self, facilities_instance):
        df = facilities_instance.data()
        assert len(df) == 2

    def test_columns_selected(self, facilities_instance):
        """COLUMNS excludes the pre-computed inflation column."""
        df = facilities_instance.data()
        assert "Total Facilities" in df.columns
        assert "Total Facilities (PWC Inflation Adj)" not in df.columns

    def test_currency_multiplied(self, facilities_instance):
        """$53,400 (thousands) should become 53,400,000."""
        df = facilities_instance.data()
        assert df["Manned Spaceflight Ground Facilities"].iloc[0] == pytest.approx(53_400_000)

    def test_monetary_columns(self):
        from tpsplots.data_sources.apollo_data_source import FacilitiesConstructionSpending

        assert len(FacilitiesConstructionSpending.MONETARY_COLUMNS) == 3

    def test_fiscal_year_detected(self, facilities_instance):
        df = facilities_instance.data()
        assert pd.api.types.is_datetime64_any_dtype(df["Year"])
