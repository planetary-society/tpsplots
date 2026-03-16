"""Tests for ApolloController methods.

Tests focus on:
- Return dict structure (correct keys, types)
- Inflation adjustment is applied to all monetary columns
- Column sums are present and are integers
- Metadata has standard keys
- Export DataFrame is built correctly

Covers: program_spending, robotic_lunar_spending, gemini_spending,
        facilities_construction_spending, launch_vehicles.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

INFLATION_MULTIPLIER = 1.5
INFLATION_TARGET_YEAR = 2025


def _mock_inflation_processor(monetary_cols: list[str]):
    """Return a mock InflationAdjustmentProcessor.process function.

    Adds ``{col}_adjusted_nnsi`` columns at ``INFLATION_MULTIPLIER`` times
    the nominal value for each monetary column.
    """

    def process(df):
        df = df.copy()
        for col in monetary_cols:
            if col in df.columns:
                df[f"{col}_adjusted_nnsi"] = df[col] * INFLATION_MULTIPLIER
        df.attrs["inflation_target_year"] = INFLATION_TARGET_YEAR
        return df

    return process


# Minimal fixture DataFrame mimicking ApolloSpending().data() output (post-cleaning).
# 3 rows, subset of columns for speed.
FIXTURE_DATA = pd.DataFrame(
    {
        "Fiscal Year": pd.to_datetime(["1960-01-01", "1961-01-01", "1962-01-01"]),
        "NASA Total Obligations": [487_000_000.0, 908_300_000.0, 1_691_600_000.0],
        "Lunar effort % of NASA": [4.0, 39.0, 57.0],
        "Lunar Effort Total": [69_120_000.0, 358_274_000.0, 971_882_000.0],
        "CSM": [0.0, 0.0, 60_000_000.0],
        "Saturn V": [0.0, 623_000.0, 57_375_000.0],
    }
)

# Subset MONETARY_COLUMNS to match fixture
FIXTURE_MONETARY = ["NASA Total Obligations", "Lunar Effort Total", "CSM", "Saturn V"]


@pytest.fixture()
def controller_result():
    """Run program_spending() with mocked Apollo data source and inflation."""
    # Mock Apollo().data() to return fixture data
    mock_apollo = MagicMock()
    mock_apollo.data.return_value = FIXTURE_DATA.copy()

    mock_processor = MagicMock()
    mock_processor.process = _mock_inflation_processor(FIXTURE_MONETARY)

    with (
        patch("tpsplots.controllers.apollo_controller.ApolloSpending", return_value=mock_apollo),
        patch(
            "tpsplots.controllers.apollo_controller.ApolloSpending.MONETARY_COLUMNS",
            FIXTURE_MONETARY,
        ),
        patch(
            "tpsplots.processors.InflationAdjustmentProcessor",
            return_value=mock_processor,
        ),
    ):
        from tpsplots.controllers.apollo_controller import Apollo

        yield Apollo().program_spending()


class TestReturnDictStructure:
    """Result dict has expected keys and types."""

    def test_has_data_key(self, controller_result):
        assert "data" in controller_result
        assert isinstance(controller_result["data"], pd.DataFrame)

    def test_has_fiscal_year(self, controller_result):
        assert "Fiscal Year" in controller_result
        assert pd.api.types.is_datetime64_any_dtype(controller_result["Fiscal Year"])

    def test_has_percentage(self, controller_result):
        assert "Lunar effort % of NASA" in controller_result

    def test_has_export_df(self, controller_result):
        assert "export_df" in controller_result
        assert isinstance(controller_result["export_df"], pd.DataFrame)

    def test_has_metadata(self, controller_result):
        assert "metadata" in controller_result
        assert isinstance(controller_result["metadata"], dict)


class TestMonetaryColumns:
    """Nominal and adjusted series are present with original column names."""

    def test_nominal_columns_present(self, controller_result):
        for col in FIXTURE_MONETARY:
            assert col in controller_result, f"Missing nominal key: {col}"

    def test_adjusted_columns_present(self, controller_result):
        for col in FIXTURE_MONETARY:
            adjusted_key = f"{col}_adjusted_nnsi"
            assert adjusted_key in controller_result, f"Missing adjusted key: {adjusted_key}"

    def test_adjusted_values_correct(self, controller_result):
        """Adjusted values should be INFLATION_MULTIPLIER x nominal (per mock)."""
        for col in FIXTURE_MONETARY:
            nominal = controller_result[col]
            adjusted = controller_result[f"{col}_adjusted_nnsi"]
            for i in range(len(nominal)):
                if nominal.iloc[i] != 0:
                    assert adjusted.iloc[i] == pytest.approx(nominal.iloc[i] * INFLATION_MULTIPLIER)
                    break


class TestColumnSums:
    """Column sums are present, are integers, and are correct."""

    def test_nominal_sums_present(self, controller_result):
        for col in FIXTURE_MONETARY:
            assert f"{col}_sum" in controller_result

    def test_adjusted_sums_present(self, controller_result):
        for col in FIXTURE_MONETARY:
            assert f"{col}_adjusted_nnsi_sum" in controller_result

    def test_sums_are_integers(self, controller_result):
        for col in FIXTURE_MONETARY:
            assert isinstance(controller_result[f"{col}_sum"], int)
            assert isinstance(controller_result[f"{col}_adjusted_nnsi_sum"], int)

    def test_nominal_sum_values(self, controller_result):
        """CSM sum should be 0 + 0 + 60M = 60M."""
        assert controller_result["CSM_sum"] == 60_000_000

    def test_adjusted_sum_values(self, controller_result):
        """Adjusted CSM sum should be 60M * INFLATION_MULTIPLIER."""
        assert controller_result["CSM_adjusted_nnsi_sum"] == int(60_000_000 * INFLATION_MULTIPLIER)


class TestMetadata:
    """Metadata has standard keys."""

    def test_has_min_fiscal_year(self, controller_result):
        meta = controller_result["metadata"]
        assert "min_fiscal_year" in meta
        assert meta["min_fiscal_year"] == 1960

    def test_has_max_fiscal_year(self, controller_result):
        meta = controller_result["metadata"]
        assert "max_fiscal_year" in meta
        assert meta["max_fiscal_year"] == 1962

    def test_has_inflation_year(self, controller_result):
        meta = controller_result["metadata"]
        assert "inflation_adjusted_year" in meta
        assert meta["inflation_adjusted_year"] == INFLATION_TARGET_YEAR

    def test_has_source(self, controller_result):
        meta = controller_result["metadata"]
        assert "source" in meta
        assert "Apollo" in meta["source"]


class TestExportDf:
    """Export DataFrame includes fiscal year and monetary columns."""

    def test_has_fiscal_year_column(self, controller_result):
        export_df = controller_result["export_df"]
        assert "Fiscal Year" in export_df.columns

    def test_has_monetary_columns(self, controller_result):
        export_df = controller_result["export_df"]
        for col in FIXTURE_MONETARY:
            assert col in export_df.columns, f"Missing export column: {col}"

    def test_has_adjusted_columns(self, controller_result):
        export_df = controller_result["export_df"]
        for col in FIXTURE_MONETARY:
            adjusted = f"{col}_adjusted_nnsi"
            assert adjusted in export_df.columns, f"Missing export adjusted column: {adjusted}"


# ────────────────────────── Helper for sub-source fixtures ──────────────────────────


def _make_spending_fixture(
    source_cls_path: str,
    monetary_columns_path: str,
    monetary_cols: list[str],
    fiscal_year_col: str,
    fiscal_years: list[str],
    data: dict,
    controller_method: str,
):
    """Build a pytest fixture that mocks a sub-source and calls its controller method."""
    fixture_df = pd.DataFrame(
        {
            fiscal_year_col: pd.to_datetime(fiscal_years),
            **data,
        }
    )

    mock_source = MagicMock()
    mock_source.data.return_value = fixture_df.copy()

    mock_processor = MagicMock()
    mock_processor.process = _mock_inflation_processor(monetary_cols)

    with (
        patch(source_cls_path, return_value=mock_source),
        patch(monetary_columns_path, monetary_cols),
        patch(
            "tpsplots.processors.InflationAdjustmentProcessor",
            return_value=mock_processor,
        ),
    ):
        from tpsplots.controllers.apollo_controller import Apollo

        return getattr(Apollo(), controller_method)()


# ────────────────────────── Robotic Lunar Programs ──────────────────────────

ROBOTIC_MONETARY = ["Ranger", "Surveyor", "Lunar Orbiter", "Total Robotic"]


@pytest.fixture()
def robotic_result():
    """Run robotic_lunar_spending() with mocked data source."""
    return _make_spending_fixture(
        source_cls_path="tpsplots.controllers.apollo_controller.RoboticLunarProgramSpending",
        monetary_columns_path="tpsplots.controllers.apollo_controller.RoboticLunarProgramSpending.MONETARY_COLUMNS",
        monetary_cols=ROBOTIC_MONETARY,
        fiscal_year_col="Year",
        fiscal_years=["1959-01-01", "1960-01-01", "1961-01-01"],
        data={
            "Ranger": [3_400_000.0, 11_700_000.0, 52_300_000.0],
            "Surveyor": [0.0, 0.0, 480_000.0],
            "Lunar Orbiter": [0.0, 0.0, 0.0],
            "Total Robotic": [3_400_000.0, 11_700_000.0, 52_780_000.0],
        },
        controller_method="robotic_lunar_spending",
    )


class TestRoboticLunarSpending:
    """Tests for ApolloController.robotic_lunar_spending()."""

    def test_has_data_key(self, robotic_result):
        assert "data" in robotic_result
        assert isinstance(robotic_result["data"], pd.DataFrame)

    def test_has_fiscal_year(self, robotic_result):
        assert "Year" in robotic_result
        assert pd.api.types.is_datetime64_any_dtype(robotic_result["Year"])

    def test_nominal_columns_present(self, robotic_result):
        for col in ROBOTIC_MONETARY:
            assert col in robotic_result, f"Missing nominal key: {col}"

    def test_adjusted_columns_present(self, robotic_result):
        for col in ROBOTIC_MONETARY:
            assert f"{col}_adjusted_nnsi" in robotic_result

    def test_sums_are_integers(self, robotic_result):
        for col in ROBOTIC_MONETARY:
            assert isinstance(robotic_result[f"{col}_sum"], int)
            assert isinstance(robotic_result[f"{col}_adjusted_nnsi_sum"], int)

    def test_ranger_sum(self, robotic_result):
        assert robotic_result["Ranger_sum"] == 67_400_000

    def test_metadata_keys(self, robotic_result):
        meta = robotic_result["metadata"]
        assert meta["min_fiscal_year"] == 1959
        assert meta["max_fiscal_year"] == 1961
        assert meta["inflation_adjusted_year"] == INFLATION_TARGET_YEAR
        assert "Robotic" in meta["source"]

    def test_export_df(self, robotic_result):
        export_df = robotic_result["export_df"]
        assert "Year" in export_df.columns
        for col in ROBOTIC_MONETARY:
            assert col in export_df.columns
            assert f"{col}_adjusted_nnsi" in export_df.columns


# ────────────────────────── Project Gemini ──────────────────────────

GEMINI_MONETARY = ["Spacecraft", "Support", "Launch Vehicle", "Total"]


@pytest.fixture()
def gemini_result():
    """Run gemini_spending() with mocked data source."""
    return _make_spending_fixture(
        source_cls_path="tpsplots.controllers.apollo_controller.ProjectGemini",
        monetary_columns_path="tpsplots.controllers.apollo_controller.ProjectGemini.MONETARY_COLUMNS",
        monetary_cols=GEMINI_MONETARY,
        fiscal_year_col="Fiscal Year",
        fiscal_years=["1962-01-01", "1963-01-01"],
        data={
            "Spacecraft": [30_600_000.0, 205_100_000.0],
            "Support": [0.0, 3_400_000.0],
            "Launch Vehicle": [24_400_000.0, 79_100_000.0],
            "Total": [55_000_000.0, 287_600_000.0],
        },
        controller_method="gemini_spending",
    )


class TestGeminiSpending:
    """Tests for ApolloController.gemini_spending()."""

    def test_has_data_key(self, gemini_result):
        assert "data" in gemini_result
        assert isinstance(gemini_result["data"], pd.DataFrame)

    def test_has_fiscal_year(self, gemini_result):
        assert "Fiscal Year" in gemini_result
        assert pd.api.types.is_datetime64_any_dtype(gemini_result["Fiscal Year"])

    def test_nominal_columns_present(self, gemini_result):
        for col in GEMINI_MONETARY:
            assert col in gemini_result

    def test_adjusted_columns_present(self, gemini_result):
        for col in GEMINI_MONETARY:
            assert f"{col}_adjusted_nnsi" in gemini_result

    def test_sums_are_integers(self, gemini_result):
        for col in GEMINI_MONETARY:
            assert isinstance(gemini_result[f"{col}_sum"], int)
            assert isinstance(gemini_result[f"{col}_adjusted_nnsi_sum"], int)

    def test_total_sum(self, gemini_result):
        assert gemini_result["Total_sum"] == 342_600_000

    def test_adjusted_total_sum(self, gemini_result):
        assert gemini_result["Total_adjusted_nnsi_sum"] == int(342_600_000 * INFLATION_MULTIPLIER)

    def test_metadata_keys(self, gemini_result):
        meta = gemini_result["metadata"]
        assert meta["min_fiscal_year"] == 1962
        assert meta["max_fiscal_year"] == 1963
        assert meta["inflation_adjusted_year"] == INFLATION_TARGET_YEAR
        assert "Gemini" in meta["source"]

    def test_export_df(self, gemini_result):
        export_df = gemini_result["export_df"]
        assert "Fiscal Year" in export_df.columns
        for col in GEMINI_MONETARY:
            assert col in export_df.columns
            assert f"{col}_adjusted_nnsi" in export_df.columns


# ────────────────────────── Facilities Construction ──────────────────────────

FACILITIES_MONETARY = [
    "Manned Spaceflight Ground Facilities",
    "Office of Tracking and Data Acquisition Facilities",
    "Total Facilities",
]


@pytest.fixture()
def facilities_result():
    """Run facilities_construction_spending() with mocked data source."""
    return _make_spending_fixture(
        source_cls_path="tpsplots.controllers.apollo_controller.FacilitiesConstructionSpending",
        monetary_columns_path="tpsplots.controllers.apollo_controller.FacilitiesConstructionSpending.MONETARY_COLUMNS",
        monetary_cols=FACILITIES_MONETARY,
        fiscal_year_col="Year",
        fiscal_years=["1961-01-01", "1962-01-01"],
        data={
            "Manned Spaceflight Ground Facilities": [53_400_000.0, 252_400_000.0],
            "Office of Tracking and Data Acquisition Facilities": [0.0, 0.0],
            "Total Facilities": [53_400_000.0, 252_400_000.0],
        },
        controller_method="facilities_construction_spending",
    )


class TestFacilitiesConstructionSpending:
    """Tests for ApolloController.facilities_construction_spending()."""

    def test_has_data_key(self, facilities_result):
        assert "data" in facilities_result
        assert isinstance(facilities_result["data"], pd.DataFrame)

    def test_has_fiscal_year(self, facilities_result):
        assert "Year" in facilities_result
        assert pd.api.types.is_datetime64_any_dtype(facilities_result["Year"])

    def test_nominal_columns_present(self, facilities_result):
        for col in FACILITIES_MONETARY:
            assert col in facilities_result

    def test_adjusted_columns_present(self, facilities_result):
        for col in FACILITIES_MONETARY:
            assert f"{col}_adjusted_nnsi" in facilities_result

    def test_sums_are_integers(self, facilities_result):
        for col in FACILITIES_MONETARY:
            assert isinstance(facilities_result[f"{col}_sum"], int)
            assert isinstance(facilities_result[f"{col}_adjusted_nnsi_sum"], int)

    def test_total_facilities_sum(self, facilities_result):
        assert facilities_result["Total Facilities_sum"] == 305_800_000

    def test_metadata_keys(self, facilities_result):
        meta = facilities_result["metadata"]
        assert meta["min_fiscal_year"] == 1961
        assert meta["max_fiscal_year"] == 1962
        assert meta["inflation_adjusted_year"] == INFLATION_TARGET_YEAR
        assert "Facilities" in meta["source"]

    def test_export_df(self, facilities_result):
        export_df = facilities_result["export_df"]
        assert "Year" in export_df.columns
        for col in FACILITIES_MONETARY:
            assert col in export_df.columns
            assert f"{col}_adjusted_nnsi" in export_df.columns


# ────────────────────────── Saturn Launch Vehicles ──────────────────────────

LAUNCH_VEHICLE_MONETARY = [
    "Saturn Launch Vehicles",
    "Saturn C-I/I",
    "Saturn IB",
    "Saturn V",
    "Engine Development",
    "Support, Development, & Operations",
]


@pytest.fixture()
def launch_vehicles_result():
    """Run launch_vehicles_spending() with mocked Apollo data source."""
    fixture_df = pd.DataFrame(
        {
            "Fiscal Year": pd.to_datetime(["1961-01-01", "1962-01-01"]),
            "Saturn Launch Vehicles": [10_000_000.0, 40_000_000.0],
            "Saturn C-I/I": [10_000_000.0, 12_000_000.0],
            "Saturn IB": [0.0, 8_000_000.0],
            "Saturn V": [0.0, 15_000_000.0],
            "Engine Development": [0.0, 3_000_000.0],
            "Support, Development, & Operations": [0.0, 2_000_000.0],
            "CSM": [1_000_000.0, 2_000_000.0],
        }
    )

    mock_apollo = MagicMock()
    mock_apollo.data.return_value = fixture_df.copy()

    mock_processor = MagicMock()
    mock_processor.process = _mock_inflation_processor(LAUNCH_VEHICLE_MONETARY)

    with (
        patch("tpsplots.controllers.apollo_controller.ApolloSpending", return_value=mock_apollo),
        patch(
            "tpsplots.processors.InflationAdjustmentProcessor",
            return_value=mock_processor,
        ),
    ):
        from tpsplots.controllers.apollo_controller import Apollo

        yield Apollo().launch_vehicles_spending()


class TestLaunchVehicles:
    """Tests for ApolloController.launch_vehicles_spending()."""

    def test_has_data_key(self, launch_vehicles_result):
        assert "data" in launch_vehicles_result
        assert isinstance(launch_vehicles_result["data"], pd.DataFrame)

    def test_has_fiscal_year(self, launch_vehicles_result):
        assert "Fiscal Year" in launch_vehicles_result
        assert pd.api.types.is_datetime64_any_dtype(launch_vehicles_result["Fiscal Year"])

    def test_includes_only_launch_vehicle_columns(self, launch_vehicles_result):
        result_df = launch_vehicles_result["data"]
        expected_columns = {
            "Fiscal Year",
            *LAUNCH_VEHICLE_MONETARY,
            *{f"{col}_adjusted_nnsi" for col in LAUNCH_VEHICLE_MONETARY},
        }
        assert set(result_df.columns) == expected_columns
        assert "CSM" not in result_df.columns

    def test_nominal_and_adjusted_columns_present(self, launch_vehicles_result):
        for col in LAUNCH_VEHICLE_MONETARY:
            assert col in launch_vehicles_result
            assert f"{col}_adjusted_nnsi" in launch_vehicles_result

    def test_total_sum(self, launch_vehicles_result):
        assert launch_vehicles_result["Saturn Launch Vehicles_sum"] == 50_000_000

    def test_metadata_keys(self, launch_vehicles_result):
        meta = launch_vehicles_result["metadata"]
        assert meta["min_fiscal_year"] == 1961
        assert meta["max_fiscal_year"] == 1962
        assert meta["inflation_adjusted_year"] == INFLATION_TARGET_YEAR
        assert "Saturn" in meta["source"]

    def test_export_df(self, launch_vehicles_result):
        export_df = launch_vehicles_result["export_df"]
        expected_columns = {
            "Fiscal Year",
            *LAUNCH_VEHICLE_MONETARY,
            *{f"{col}_adjusted_nnsi" for col in LAUNCH_VEHICLE_MONETARY},
        }
        assert set(export_df.columns) == expected_columns
