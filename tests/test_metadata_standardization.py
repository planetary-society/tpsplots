"""Tests verifying _build_metadata() standardization across all controllers.

Each test ensures the controller's output includes a 'metadata' dict key
with expected sub-keys, using monkeypatching to avoid real data sources.
"""

from datetime import datetime

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# CSVController
# ---------------------------------------------------------------------------


class TestCSVControllerMetadata:
    def test_csv_with_fiscal_year_column(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Amount\n2020,100\n2021,200\n")

        from tpsplots.controllers.csv_controller import CSVController

        ctrl = CSVController(csv_path=str(csv_file))
        result = ctrl.load_data()

        assert "metadata" in result
        assert result["metadata"]["max_fiscal_year"] is not None
        assert result["metadata"]["min_fiscal_year"] is not None

    def test_csv_without_fiscal_year_column(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Name,Value\nA,1\nB,2\n")

        from tpsplots.controllers.csv_controller import CSVController

        ctrl = CSVController(csv_path=str(csv_file))
        result = ctrl.load_data()

        assert "metadata" in result
        # No FY column → no fiscal year keys
        assert "max_fiscal_year" not in result["metadata"]


# ---------------------------------------------------------------------------
# GoogleSheetsController
# ---------------------------------------------------------------------------


class TestGoogleSheetsControllerMetadata:
    def test_metadata_key_present(self, monkeypatch):
        dummy_df = pd.DataFrame({"Fiscal Year": [2020, 2021], "Budget": [100, 200]})

        class _StubSource:
            def __init__(self, **kwargs):
                pass

            def data(self):
                return dummy_df

        monkeypatch.setattr(
            "tpsplots.controllers.google_sheets_controller.GoogleSheetsSource",
            _StubSource,
        )

        from tpsplots.controllers.google_sheets_controller import GoogleSheetsController

        ctrl = GoogleSheetsController(url="https://example.com/sheet")
        result = ctrl.load_data()

        assert "metadata" in result
        assert result["metadata"]["max_fiscal_year"] == 2021
        assert result["metadata"]["min_fiscal_year"] == 2020


# ---------------------------------------------------------------------------
# ComparisonCharts
# ---------------------------------------------------------------------------


class TestComparisonChartsMetadata:
    def test_metadata_and_top_level_keys_preserved(self):
        from tpsplots.controllers.comparison_charts_controller import ComparisonCharts

        ctrl = ComparisonCharts()
        result = ctrl.nasa_spending_as_part_of_annual_us_expenditures()

        # All existing top-level keys preserved
        for key in (
            "fiscal_year",
            "source",
            "block_value",
            "values",
            "labels",
            "export_df",
            "data",
        ):
            assert key in result, f"Missing top-level key: {key}"

        # Metadata present with expected sub-keys
        assert "metadata" in result
        assert result["metadata"]["source"] == "Congressional Budget Office, FY 2024"
        assert result["metadata"]["max_fiscal_year"] == 2024
        assert result["metadata"]["min_fiscal_year"] == 2024
        assert result["metadata"]["block_value"] == 25_000_000_000


# ---------------------------------------------------------------------------
# ChinaComparisonCharts
# ---------------------------------------------------------------------------


class TestChinaComparisonChartsMetadata:
    @pytest.fixture()
    def _stub_data_sources(self, monkeypatch):
        """Stub both data sources used by ChinaComparisonCharts."""

        china_df = pd.DataFrame(
            {
                "Mission Name": ["Mission A"],
                "Launch Date": ["2022-01-01"],
                "Area": ["Planetary"],
                "Source": ["CNSA"],
                "Mass": ["1000 kg"],
            }
        )

        class _StubGoogleSheets:
            def __init__(self, **kwargs):
                pass

            def data(self):
                return china_df

        us_df = pd.DataFrame(
            {
                "Full Name": ["Mission B"],
                "Mission Launch Date": ["2021-06-15"],
                "Nation": ["United States of America"],
                "Mass (kg)": [2000],
            }
        )

        class _StubSpaceScienceMissions:
            def data(self):
                return us_df

        monkeypatch.setattr(
            "tpsplots.controllers.china_comparisons_controller.GoogleSheetsSource",
            _StubGoogleSheets,
        )
        monkeypatch.setattr(
            "tpsplots.data_sources.space_science_missions.SpaceScienceMissions",
            _StubSpaceScienceMissions,
        )

    @pytest.mark.usefixtures("_stub_data_sources")
    def test_bar_chart_has_metadata(self):
        from tpsplots.controllers.china_comparisons_controller import ChinaComparisonCharts

        ctrl = ChinaComparisonCharts()
        result = ctrl.china_space_science_mission_count_bar_chart()

        assert "metadata" in result
        assert result["metadata"]["source"] == ChinaComparisonCharts.SOURCE

    @pytest.mark.usefixtures("_stub_data_sources")
    def test_line_chart_has_metadata(self):
        from tpsplots.controllers.china_comparisons_controller import ChinaComparisonCharts

        ctrl = ChinaComparisonCharts()
        result = ctrl.china_space_science_mission_mass_growth_line_chart()

        assert "metadata" in result
        assert result["metadata"]["source"] == ChinaComparisonCharts.SOURCE


# ---------------------------------------------------------------------------
# NASABudgetChart — donut chart
# ---------------------------------------------------------------------------


class TestNASABudgetChartDonutMetadata:
    def test_donut_has_metadata_with_total_budget(self, monkeypatch):
        dummy_df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2024, 1, 1)],
                "Science": [7_000_000_000],
                "Aeronautics": [1_000_000_000],
                "Deep Space Exploration Systems": [8_000_000_000],
                "Space Operations": [4_000_000_000],
                "Space Technology": [1_500_000_000],
                "Facilities, IT, & Salaries": [3_000_000_000],
                "STEM Education": [150_000_000],
            }
        )

        class _StubDirectorates:
            def data(self):
                return dummy_df

        monkeypatch.setattr(
            "tpsplots.controllers.nasa_budget_chart.Directorates",
            _StubDirectorates,
        )

        from tpsplots.controllers.nasa_budget_chart import NASABudgetChart

        ctrl = NASABudgetChart()
        result = ctrl.nasa_major_activites_donut_chart()

        assert "metadata" in result
        assert "total_budget" in result["metadata"]
        assert result["metadata"]["total_budget"] > 0
        assert "source" in result["metadata"]
        assert "max_fiscal_year" in result["metadata"]


# ---------------------------------------------------------------------------
# NASAFYChartsController
# ---------------------------------------------------------------------------


class TestNASAFYChartsControllerMetadata:
    """Test metadata on NASAFYChartsController methods via NASAFY2026Controller stubs."""

    @pytest.fixture()
    def stub_controller(self, monkeypatch):
        """Create a NASAFY2026Controller with stubbed data sources."""
        from tpsplots.controllers.nasa_fy2026_controller import NASAFY2026Controller

        # Stub budget detail (minimal DataFrame)
        budget_detail = pd.DataFrame(
            {
                "Account": ["Total", "Science"],
                "FY 2026 Request": [25_000_000_000, 7_000_000_000],
            }
        )

        # Create controller bypassing __init__
        ctrl = object.__new__(NASAFY2026Controller)
        ctrl.budget_detail = budget_detail
        return ctrl

    def test_get_award_data_has_metadata(self, stub_controller, monkeypatch):
        award_df = pd.DataFrame(
            {
                "Award Type": ["Grant", "Grant"],
                "Recipient": ["MIT", "Stanford"],
                "Amount": [1_000_000, 2_000_000],
            }
        )

        class _StubProcessor:
            def __init__(self, **kwargs):
                pass

            def process(self, df):
                return award_df

        monkeypatch.setattr(
            "tpsplots.controllers.nasa_fy_charts_controller.AwardDataProcessor",
            _StubProcessor,
        )

        # Stub new_awards cached property
        stub_controller.__dict__["new_awards"] = pd.DataFrame()

        result = stub_controller._get_award_data(award_type="Grant")

        assert "metadata" in result

    def test_directorates_comparison_raw_has_metadata(self, stub_controller, monkeypatch):
        df = pd.DataFrame(
            {
                "Account": ["Science", "Exploration"],
                "FY 2026 Request": [7_000_000_000, 8_000_000_000],
            }
        )

        monkeypatch.setattr(
            type(stub_controller),
            "_directorates_comparison",
            lambda self: df,
        )

        result = stub_controller.directorates_comparison_raw()

        assert "metadata" in result

    def test_directorates_comparison_grouped_has_metadata(self, stub_controller, monkeypatch):
        df = pd.DataFrame(
            {
                "Account": ["Science", "Exploration"],
                "FY 2025 Enacted": [6_000_000_000, 7_000_000_000],
                "FY 2026 Request": [7_000_000_000, 8_000_000_000],
            }
        )

        monkeypatch.setattr(
            type(stub_controller),
            "_directorates_comparison",
            lambda self: df,
        )

        result = stub_controller.directorates_comparison_grouped()

        assert "metadata" in result


# ---------------------------------------------------------------------------
# NASAFY2026Controller — custom methods
# ---------------------------------------------------------------------------


class TestNASAFY2026ControllerMetadata:
    def test_workforce_map_has_metadata(self):
        from tpsplots.controllers.nasa_fy2026_controller import NASAFY2026Controller

        ctrl = object.__new__(NASAFY2026Controller)
        result = ctrl.nasa_center_workforce_map()

        assert "metadata" in result
        # All existing keys preserved
        assert "pie_data" in result
        assert "export_df" in result

    def test_cancelled_missions_has_metadata(self, monkeypatch):
        class _StubMissions:
            def data(self):
                return pd.DataFrame(
                    {
                        "Mission": ["Alpha (A)", "Beta"],
                        "Launch Date": [datetime(2010, 1, 1), datetime(2012, 1, 1)],
                        "Formulation Start": [datetime(2005, 1, 1), datetime(2007, 1, 1)],
                        "LCC": [1_000_000_000, 2_000_000_000],
                        "NASA Led?": [True, True],
                        "Status": ["Prime Mission", "Extended Mission"],
                    }
                )

        monkeypatch.setattr(
            "tpsplots.controllers.nasa_fy2026_controller.Missions",
            _StubMissions,
        )

        from tpsplots.controllers.nasa_fy2026_controller import NASAFY2026Controller

        ctrl = object.__new__(NASAFY2026Controller)
        result = ctrl.cancelled_missions_lollipop_chart()

        assert "metadata" in result
        # Existing keys preserved
        assert "total_projects" in result
        assert "total_value" in result
        assert "total_development_time" in result
