"""Tests for ChartController._export_helper."""

import pandas as pd
import pytest

from tpsplots.controllers.chart_controller import ChartController


@pytest.fixture
def controller():
    return ChartController()


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "Fiscal Year": pd.to_datetime(["2020-01-01", "2021-01-01", "2022-01-01"]),
            "Budget": [1234.5678, 2345.6789, 3456.7891],
            "Percent": [0.12345, 0.23456, 0.34567],
            "Label": ["Alpha", "Beta", "Gamma"],
        }
    )


class TestExportHelperDefaultRounding:
    def test_default_rounding_is_2dp(self, controller, sample_df):
        result = controller._export_helper(sample_df, ["Fiscal Year", "Budget", "Percent"])
        assert list(result["Budget"]) == [1234.57, 2345.68, 3456.79]
        assert list(result["Percent"]) == [0.12, 0.23, 0.35]

    def test_rounding_none_uses_default(self, controller, sample_df):
        result = controller._export_helper(sample_df, ["Fiscal Year", "Budget"], rounding=None)
        assert list(result["Budget"]) == [1234.57, 2345.68, 3456.79]


class TestExportHelperColumnOverrides:
    def test_column_specific_override(self, controller, sample_df):
        result = controller._export_helper(
            sample_df,
            ["Fiscal Year", "Budget", "Percent"],
            rounding={"Budget": 0, "Percent": 4},
        )
        assert list(result["Budget"]) == [1235.0, 2346.0, 3457.0]
        assert list(result["Percent"]) == [0.1234, 0.2346, 0.3457]

    def test_unspecified_columns_use_default(self, controller, sample_df):
        result = controller._export_helper(
            sample_df,
            ["Fiscal Year", "Budget", "Percent"],
            rounding={"Budget": 0},
        )
        # Budget uses override, Percent falls back to default 2dp
        assert list(result["Budget"]) == [1235.0, 2346.0, 3457.0]
        assert list(result["Percent"]) == [0.12, 0.23, 0.35]


class TestExportHelperFiscalYear:
    def test_fiscal_year_formatted(self, controller, sample_df):
        result = controller._export_helper(sample_df, ["Fiscal Year", "Budget"])
        assert list(result["Fiscal Year"]) == ["2020", "2021", "2022"]

    def test_fiscal_year_string_fallback(self, controller):
        df = pd.DataFrame({"Fiscal Year": ["FY2020", "FY2021"], "Value": [1.111, 2.222]})
        result = controller._export_helper(df, ["Fiscal Year", "Value"])
        # Non-datetime strings fall back to str conversion
        assert list(result["Fiscal Year"]) == ["FY2020", "FY2021"]


class TestExportHelperStringColumns:
    def test_string_columns_preserved(self, controller, sample_df):
        result = controller._export_helper(sample_df, ["Fiscal Year", "Label"])
        assert list(result["Label"]) == ["Alpha", "Beta", "Gamma"]
