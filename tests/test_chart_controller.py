"""Tests for ChartController._build_metadata and related helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from tpsplots.controllers.chart_controller import ChartController


@pytest.fixture
def controller():
    return ChartController()


# ── FY extraction ──


class TestBuildMetadataFYExtraction:
    """Tests for fiscal year extraction from different column types."""

    def test_datetime_fy_column(self, controller):
        df = pd.DataFrame(
            {"Fiscal Year": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01"])}
        )
        metadata = controller._build_metadata(df)
        assert metadata["max_fiscal_year"] == 2022
        assert metadata["min_fiscal_year"] == 2020

    def test_integer_fy_column(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2018, 2019, 2020, 2021]})
        metadata = controller._build_metadata(df)
        assert metadata["max_fiscal_year"] == 2021
        assert metadata["min_fiscal_year"] == 2018

    def test_string_fy_column(self, controller):
        df = pd.DataFrame({"Fiscal Year": ["2015-01-01", "2016-01-01", "2017-01-01"]})
        metadata = controller._build_metadata(df)
        assert metadata["max_fiscal_year"] == 2017
        assert metadata["min_fiscal_year"] == 2015

    def test_fiscal_year_col_none_skips_fy(self, controller):
        df = pd.DataFrame({"Amount": [100, 200]})
        metadata = controller._build_metadata(df, fiscal_year_col=None)
        assert "max_fiscal_year" not in metadata
        assert "min_fiscal_year" not in metadata

    def test_missing_fy_column_skips_fy(self, controller):
        df = pd.DataFrame({"Amount": [100, 200]})
        metadata = controller._build_metadata(df, fiscal_year_col="Fiscal Year")
        assert "max_fiscal_year" not in metadata
        assert "min_fiscal_year" not in metadata

    def test_custom_fy_column_name(self, controller):
        df = pd.DataFrame({"Year": [2010, 2011, 2012]})
        metadata = controller._build_metadata(df, fiscal_year_col="Year")
        assert metadata["max_fiscal_year"] == 2012
        assert metadata["min_fiscal_year"] == 2010


# ── FY overrides ──


class TestBuildMetadataFYOverrides:
    """Tests for explicit max/min fiscal year overrides."""

    def test_max_fy_override(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020, 2021, 2022]})
        metadata = controller._build_metadata(df, max_fiscal_year=2025)
        assert metadata["max_fiscal_year"] == 2025
        assert metadata["min_fiscal_year"] == 2020

    def test_min_fy_override(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020, 2021, 2022]})
        metadata = controller._build_metadata(df, min_fiscal_year=2008)
        assert metadata["max_fiscal_year"] == 2022
        assert metadata["min_fiscal_year"] == 2008

    def test_both_fy_overrides(self, controller):
        df = pd.DataFrame({"Amount": [100]})
        metadata = controller._build_metadata(
            df, fiscal_year_col=None, max_fiscal_year=2025, min_fiscal_year=2024
        )
        assert metadata["max_fiscal_year"] == 2025
        assert metadata["min_fiscal_year"] == 2024

    def test_overrides_replace_extracted_values(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020, 2021, 2022]})
        metadata = controller._build_metadata(df, max_fiscal_year=2030, min_fiscal_year=2000)
        assert metadata["max_fiscal_year"] == 2030
        assert metadata["min_fiscal_year"] == 2000


# ── Value columns ──


class TestBuildMetadataValueColumns:
    """Tests for per-column FY ranges and value statistics."""

    def test_value_columns_fy_ranges(self, controller):
        df = pd.DataFrame(
            {
                "Fiscal Year": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01"]),
                "Budget": [100.0, None, 300.0],
            }
        )
        metadata = controller._build_metadata(df, value_columns={"budget": "Budget"})
        assert metadata["max_budget_fiscal_year"] == 2022
        assert metadata["min_budget_fiscal_year"] == 2020

    def test_value_columns_value_stats(self, controller):
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022],
                "Budget": [100.0, 250.0, 300.0],
            }
        )
        metadata = controller._build_metadata(df, value_columns={"budget": "Budget"})
        assert metadata["max_budget"] == 300.0
        assert metadata["min_budget"] == 100.0

    def test_value_columns_skip_nan_for_stats(self, controller):
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022, 2023],
                "Amount": [None, 50.0, 200.0, None],
            }
        )
        metadata = controller._build_metadata(df, value_columns={"amount": "Amount"})
        assert metadata["max_amount"] == 200.0
        assert metadata["min_amount"] == 50.0
        assert metadata["max_amount_fiscal_year"] == 2022
        assert metadata["min_amount_fiscal_year"] == 2021

    def test_value_columns_missing_column_skipped(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020], "A": [1.0]})
        metadata = controller._build_metadata(df, value_columns={"missing": "NonExistent"})
        assert "max_missing" not in metadata
        assert "max_missing_fiscal_year" not in metadata

    def test_value_columns_without_fy_series(self, controller):
        """value_columns are skipped when fiscal_year_col is None."""
        df = pd.DataFrame({"Amount": [100.0, 200.0]})
        metadata = controller._build_metadata(
            df, fiscal_year_col=None, value_columns={"amount": "Amount"}
        )
        assert "max_amount" not in metadata
        assert "max_amount_fiscal_year" not in metadata

    def test_multiple_value_columns(self, controller):
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022],
                "PBR": [10.0, 20.0, 30.0],
                "Appropriation": [15.0, None, 35.0],
            }
        )
        metadata = controller._build_metadata(
            df,
            value_columns={"pbr": "PBR", "appropriation": "Appropriation"},
        )
        assert metadata["max_pbr"] == 30.0
        assert metadata["min_pbr"] == 10.0
        assert metadata["max_appropriation"] == 35.0
        assert metadata["min_appropriation"] == 15.0


# ── Inflation metadata ──


class TestBuildMetadataInflation:
    """Tests for inflation_adjusted_year auto-extraction."""

    def test_inflation_year_from_attrs(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020]})
        df.attrs["inflation_target_year"] = 2024
        metadata = controller._build_metadata(df)
        assert metadata["inflation_adjusted_year"] == 2024

    def test_no_inflation_attrs(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020]})
        metadata = controller._build_metadata(df)
        assert "inflation_adjusted_year" not in metadata


# ── Source ──


class TestBuildMetadataSource:
    """Tests for source parameter."""

    def test_source_set(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020]})
        metadata = controller._build_metadata(df, source="NASA Budget Data")
        assert metadata["source"] == "NASA Budget Data"

    def test_source_none_omitted(self, controller):
        df = pd.DataFrame({"Fiscal Year": [2020]})
        metadata = controller._build_metadata(df)
        assert "source" not in metadata


# ── Standalone _add_inflation_adjusted_year_metadata ──


class TestAddInflationMetadata:
    """Tests for the standalone static method."""

    def test_adds_inflation_year(self):
        df = pd.DataFrame({"x": [1]})
        df.attrs["inflation_target_year"] = 2025
        metadata: dict = {}
        ChartController._add_inflation_adjusted_year_metadata(metadata, df)
        assert metadata["inflation_adjusted_year"] == 2025

    def test_no_attrs_no_change(self):
        df = pd.DataFrame({"x": [1]})
        metadata: dict = {}
        ChartController._add_inflation_adjusted_year_metadata(metadata, df)
        assert "inflation_adjusted_year" not in metadata

    def test_returns_same_dict(self):
        df = pd.DataFrame({"x": [1]})
        metadata: dict = {"existing": "value"}
        result = ChartController._add_inflation_adjusted_year_metadata(metadata, df)
        assert result is metadata
        assert result["existing"] == "value"
