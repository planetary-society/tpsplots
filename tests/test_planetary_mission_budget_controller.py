"""Tests for PlanetaryMissionBudgetController dynamic method generation."""

from pathlib import Path

import pandas as pd
import pytest

from tpsplots.controllers.planetary_mission_budget import (
    PlanetaryMissionBudgetController,
    _tab_to_method_name,
)
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


class _NoOpInflationConfig:
    """Dummy config that records kwargs and exposes a fixed target year."""

    def __init__(self, **kwargs):
        self.target_year = 2025
        self.nnsi_columns = kwargs.get("nnsi_columns", [])
        self.fiscal_year_column = kwargs.get("fiscal_year_column", "Fiscal Year")


class _NoOpInflationProcessor:
    """No-op processor that creates ``{col}_adjusted_nnsi`` columns as identity copies."""

    def __init__(self, config):
        self._config = config

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in self._config.nnsi_columns:
            if col in df.columns:
                df[f"{col}_adjusted_nnsi"] = df[col]
        df.attrs["inflation_target_year"] = self._config.target_year
        return df


@pytest.fixture()
def mock_inflation(monkeypatch):
    """Patch deferred inflation imports inside the controller's _load_tab."""
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentConfig",
        _NoOpInflationConfig,
    )
    monkeypatch.setattr(
        "tpsplots.processors.InflationAdjustmentProcessor",
        _NoOpInflationProcessor,
    )


# ── Name conversion ──


class TestTabToMethodName:
    @pytest.mark.parametrize(
        ("tab", "expected"),
        [
            ("Cassini", "cassini"),
            ("Europa Clipper", "europa_clipper"),
            ("FY 2026", "fy_2026"),
            ("FY 1976 TQ", "fy_1976_tq"),
            ("Pioneer 10 & 11", "pioneer_10_11"),
            ("MPL/MCO", "mpl_mco"),
            ("OSIRIS-REx", "osiris_rex"),
            ("Mariner 8 & 9", "mariner_8_9"),
            ("MSL Curiosity", "msl_curiosity"),
            ("Deep Space 1", "deep_space_1"),
            ("Mars Sample Return", "mars_sample_return"),
            ("Major Programs, 1994 - current", "major_programs_1994_current"),
            ("Budget History (inflation adj)", "budget_history_inflation_adj"),
            ("US Spending & Outlays", "us_spending_outlays"),
            ("SIMPLEx Program", "simplex_program"),
            ("NNSI", "nnsi"),
        ],
    )
    def test_conversion(self, tab, expected):
        assert _tab_to_method_name(tab) == expected


# ── Method generation ──


class TestMethodGeneration:
    def test_mission_methods_exist(self):
        for name in ["cassini", "europa_clipper", "voyager", "juno", "dawn"]:
            assert callable(getattr(PlanetaryMissionBudgetController, name, None)), (
                f"Method '{name}' not found on class"
            )

    def test_fy_methods_exist(self):
        for name in ["fy_2026", "fy_2025", "fy_1976_tq", "fy_1959"]:
            assert callable(getattr(PlanetaryMissionBudgetController, name, None)), (
                f"Method '{name}' not found on class"
            )

    def test_aggregate_methods_exist(self):
        for name in [
            "planetary_science_budget_history",
            "mission_costs",
            "funding_by_destination",
        ]:
            assert callable(getattr(PlanetaryMissionBudgetController, name, None)), (
                f"Method '{name}' not found on class"
            )

    def test_metadata_tabs_excluded(self):
        assert getattr(PlanetaryMissionBudgetController, "introduction", None) is None
        assert getattr(PlanetaryMissionBudgetController, "charts", None) is None

    def test_no_method_name_collisions(self):
        """All generated method names must be unique."""
        methods = PlanetaryMissionBudgetController.available_methods()
        assert len(methods) == len(set(methods.keys()))

    def test_available_methods_count(self):
        """Should have methods for all tabs minus excluded ones."""
        methods = PlanetaryMissionBudgetController.available_methods()
        expected = len(PlanetaryBudgetDataSource.TAB_GID_LOOKUP) - 2  # minus Introduction, Charts
        assert len(methods) == expected

    def test_available_methods_values_are_canonical_tab_names(self):
        methods = PlanetaryMissionBudgetController.available_methods()
        assert methods["cassini"] == "Cassini"
        assert methods["europa_clipper"] == "Europa Clipper"
        assert methods["fy_2026"] == "FY 2026"

    def test_dir_includes_generated_methods(self):
        controller = PlanetaryMissionBudgetController()
        members = dir(controller)
        assert "cassini" in members
        assert "europa_clipper" in members
        assert "fy_2026" in members


# ── Data flow ──


class TestDataFlow:
    def test_method_returns_dict_with_data_key(self, mock_fetch_csv, mock_inflation):
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        assert isinstance(result, dict)
        assert "data" in result
        assert isinstance(result["data"], pd.DataFrame)

    def test_method_returns_column_arrays(self, mock_fetch_csv, mock_inflation):
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        assert "Fiscal Year" in result
        assert "Total Cost" in result

    def test_method_returns_metadata(self, mock_fetch_csv, mock_inflation):
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        assert "metadata" in result
        assert result["metadata"]["tab_name"] == "Cassini"
        assert "Planetary" in result["metadata"]["source"]

    def test_generated_method_has_name_and_doc(self):
        method = PlanetaryMissionBudgetController.cassini
        assert method.__name__ == "cassini"
        assert "Cassini" in method.__doc__


# ── Inflation adjustment integration ──


class TestInflationAdjustment:
    def test_adjusted_columns_created(self, mock_fetch_csv, mock_inflation):
        """Controller should create _adjusted_nnsi columns for monetary columns."""
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        # The fixture has monetary columns: Spacecraft Development, Launch Support, etc.
        assert "Total Cost_adjusted_nnsi" in result
        assert "Spacecraft Development_adjusted_nnsi" in result

    def test_adjusted_columns_in_dataframe(self, mock_fetch_csv, mock_inflation):
        """Adjusted columns should also exist in the underlying DataFrame."""
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        df = result["data"]
        assert "Total Cost_adjusted_nnsi" in df.columns
        assert "Spacecraft Development_adjusted_nnsi" in df.columns

    def test_metadata_includes_inflation_year(self, mock_fetch_csv, mock_inflation):
        """Metadata should expose the inflation target year."""
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        assert result["metadata"]["inflation_adjusted_year"] == 2025

    def test_non_monetary_columns_not_adjusted(self, mock_fetch_csv, mock_inflation):
        """Fiscal Year, Notes, Official LCC should not get _adjusted_nnsi columns."""
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        assert "Fiscal Year_adjusted_nnsi" not in result
        assert "Notes_adjusted_nnsi" not in result
        assert "Official LCC_adjusted_nnsi" not in result

    def test_adjusted_values_are_numeric(self, mock_fetch_csv, mock_inflation):
        """Adjusted column values should be numeric (not strings)."""
        controller = PlanetaryMissionBudgetController()
        result = controller.cassini()
        df = result["data"]
        assert pd.api.types.is_numeric_dtype(df["Total Cost_adjusted_nnsi"])
