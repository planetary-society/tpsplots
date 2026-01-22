"""Tests for DataFrameToYAMLProcessor.

Tests focus on:
- Column names retained exactly as-is
- DataFrame attrs preservation
- Export DataFrame building
- Export note generation
- Max fiscal year computation
"""

from datetime import datetime

import pandas as pd
import pytest

from tpsplots.processors.dataframe_to_yaml_processor import (
    DataFrameToYAMLConfig,
    DataFrameToYAMLProcessor,
)


class TestDataFrameToYAMLProcessor:
    """Tests for DataFrameToYAMLProcessor."""

    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with typical columns."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2024, 2027)],
                "PBR": [100, 110, 120],
                "Appropriation": [95, 105, 115],
                "White House Budget Projection": [None, None, 120],
            }
        )
        df.attrs["fiscal_year"] = 2026
        df.attrs["inflation_target_year"] = 2025
        df.attrs["current_pbr_request"] = 120
        df.attrs["pbr_column"] = "PBR"
        df.attrs["appropriation_column"] = "Appropriation"
        return df

    def test_returns_dict(self, sample_df):
        """Processor should return a dict."""
        result = DataFrameToYAMLProcessor().process(sample_df)
        assert isinstance(result, dict)

    def test_columns_retain_original_names(self, sample_df):
        """Column names should be retained exactly as-is."""
        result = DataFrameToYAMLProcessor().process(sample_df)

        assert "Fiscal Year" in result
        assert "PBR" in result
        assert "Appropriation" in result
        assert "White House Budget Projection" in result

    def test_column_values_are_series(self, sample_df):
        """Each column key should map to a pandas Series."""
        result = DataFrameToYAMLProcessor().process(sample_df)

        assert isinstance(result["Fiscal Year"], pd.Series)
        assert isinstance(result["PBR"], pd.Series)
        assert list(result["PBR"]) == [100, 110, 120]

    def test_export_df_included(self, sample_df):
        """export_df key should contain a DataFrame."""
        result = DataFrameToYAMLProcessor().process(sample_df)

        assert "export_df" in result
        assert isinstance(result["export_df"], pd.DataFrame)

    def test_attrs_included_in_output(self, sample_df):
        """DataFrame attrs should be included in output."""
        result = DataFrameToYAMLProcessor().process(sample_df)

        assert result.get("fiscal_year") is not None  # Could be Series or attr
        assert result.get("inflation_target_year") == 2025
        assert result.get("current_pbr_request") == 120

    def test_max_fiscal_year_computed(self, sample_df):
        """max_fiscal_year should be computed from data."""
        result = DataFrameToYAMLProcessor().process(sample_df)

        assert result["max_fiscal_year"] == 2026

    def test_custom_export_df_key(self, sample_df):
        """Custom export_df_key should be used."""
        config = DataFrameToYAMLConfig(export_df_key="data_export")
        result = DataFrameToYAMLProcessor(config).process(sample_df)

        assert "data_export" in result
        assert "export_df" not in result


class TestExportDataFrame:
    """Tests for export DataFrame building."""

    @pytest.fixture
    def sample_df_with_projection(self):
        """Create DataFrame with projection values to be cleared."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(y, 1, 1) for y in range(2024, 2028)],
                "Appropriation": [100, 105, None, None],
                "White House Budget Projection": [100, 105, 120, 125],
            }
        )
        df.attrs["fiscal_year"] = 2026
        return df

    def test_projection_cleared_for_historical_years(self, sample_df_with_projection):
        """White House Budget Projection should be cleared for FY <= current."""
        result = DataFrameToYAMLProcessor().process(sample_df_with_projection)
        export_df = result["export_df"]

        # FY2024, FY2025, FY2026 should have projection cleared
        assert pd.isna(export_df.loc[0, "White House Budget Projection"])
        assert pd.isna(export_df.loc[1, "White House Budget Projection"])
        assert pd.isna(export_df.loc[2, "White House Budget Projection"])

        # FY2027 (future) should keep projection
        assert export_df.loc[3, "White House Budget Projection"] == 125

    def test_projection_not_cleared_when_disabled(self, sample_df_with_projection):
        """When clear_projection_before_fy is False, keep all values."""
        config = DataFrameToYAMLConfig(clear_projection_before_fy=False)
        result = DataFrameToYAMLProcessor(config).process(sample_df_with_projection)
        export_df = result["export_df"]

        # All projection values should be preserved
        assert export_df.loc[0, "White House Budget Projection"] == 100
        assert export_df.loc[1, "White House Budget Projection"] == 105


class TestExportNote:
    """Tests for export note generation."""

    @pytest.fixture
    def df_with_attrs(self):
        """Create DataFrame with attrs for export note."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1), datetime(2026, 1, 1)],
                "Appropriation": [24_875_000_000, None],
                "PBR": [None, 25_000_000_000],
            }
        )
        df.attrs["fiscal_year"] = 2026
        df.attrs["inflation_target_year"] = 2025
        df.attrs["current_pbr_request"] = 25_000_000_000
        df.attrs["appropriation_column"] = "Appropriation"
        return df

    def test_default_export_note_includes_inflation(self, df_with_attrs):
        """Default export note should include inflation year."""
        result = DataFrameToYAMLProcessor().process(df_with_attrs)
        export_df = result["export_df"]

        assert "export_note" in export_df.attrs
        assert "FY 2025 dollars" in export_df.attrs["export_note"]

    def test_export_note_includes_yoy_change(self, df_with_attrs):
        """Export note should include YoY change when computable."""
        result = DataFrameToYAMLProcessor().process(df_with_attrs)
        export_df = result["export_df"]

        export_note = export_df.attrs["export_note"]
        # Should mention the change percentage
        assert "FY 2026 PBR" in export_note
        assert "increase" in export_note or "decrease" in export_note

    def test_custom_export_note_template(self, df_with_attrs):
        """Custom export note template should be used."""
        config = DataFrameToYAMLConfig(
            export_note_template="Data for FY {fiscal_year}. Target year: {inflation_target_year}."
        )
        result = DataFrameToYAMLProcessor(config).process(df_with_attrs)
        export_df = result["export_df"]

        assert export_df.attrs["export_note"] == "Data for FY 2026. Target year: 2025."


class TestColumnFiltering:
    """Tests for columns_to_export configuration."""

    @pytest.fixture
    def multi_column_df(self):
        """Create DataFrame with many columns."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1)],
                "Column A": [1],
                "Column B": [2],
                "Column C": [3],
                "Column D": [4],
            }
        )
        return df

    def test_all_columns_by_default(self, multi_column_df):
        """All columns should be included by default."""
        result = DataFrameToYAMLProcessor().process(multi_column_df)

        assert "Fiscal Year" in result
        assert "Column A" in result
        assert "Column B" in result
        assert "Column C" in result
        assert "Column D" in result

    def test_filter_columns(self, multi_column_df):
        """Only specified columns should be included."""
        config = DataFrameToYAMLConfig(columns_to_export=["Fiscal Year", "Column A", "Column C"])
        result = DataFrameToYAMLProcessor(config).process(multi_column_df)

        assert "Fiscal Year" in result
        assert "Column A" in result
        assert "Column C" in result
        # Column B and D should not be in output
        assert "Column B" not in result
        assert "Column D" not in result


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_dataframe(self):
        """Empty DataFrame should produce empty dict with export_df."""
        df = pd.DataFrame()
        result = DataFrameToYAMLProcessor().process(df)

        assert "export_df" in result
        assert isinstance(result["export_df"], pd.DataFrame)
        assert result["export_df"].empty

    def test_no_fiscal_year_column(self):
        """DataFrame without Fiscal Year should still work."""
        df = pd.DataFrame({"Value": [1, 2, 3]})
        result = DataFrameToYAMLProcessor().process(df)

        assert "Value" in result
        assert "max_fiscal_year" not in result  # Can't compute without FY column

    def test_integer_fiscal_years(self):
        """Integer fiscal years (not datetime) should work."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [2024, 2025, 2026],
                "Value": [100, 110, 120],
            }
        )
        result = DataFrameToYAMLProcessor().process(df)

        assert result["max_fiscal_year"] == 2026

    def test_attrs_dont_overwrite_columns(self):
        """DataFrame attrs should not overwrite column data."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [datetime(2025, 1, 1)],
                "Value": [100],
            }
        )
        # Add an attr with same name as column
        df.attrs["Value"] = "attr_value"

        result = DataFrameToYAMLProcessor().process(df)

        # Column data should take precedence
        assert isinstance(result["Value"], pd.Series)
        assert result["Value"].iloc[0] == 100
