"""Tests for FiscalYearMixin functionality."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from tpsplots.data_sources.fiscal_year_mixin import FY_COLUMN_PATTERN, FiscalYearMixin


class TestFYColumnPattern:
    """Test the regular expression pattern for detecting FY columns."""

    @pytest.mark.parametrize(
        "column_name",
        [
            "Fiscal Year",
            "fiscal year",
            "FISCAL YEAR",
            "FiscalYear",
            "fiscalyear",
            "FY",
            "fy",
            "FY2024",
            "FY24",
            "fy2024",
            "Year",
            "year",
            "YEAR",
        ],
    )
    def test_pattern_matches_fy_columns(self, column_name):
        """Pattern should match common fiscal year column names."""
        assert FY_COLUMN_PATTERN.match(column_name) is not None

    @pytest.mark.parametrize(
        "column_name",
        [
            "Date",
            "Budget Year",
            "Calendar Year",
            "YearEnd",
            "Fiscal_Year",
            "FY_2024",
            "Amount",
            "FiscalYearEnd",
        ],
    )
    def test_pattern_does_not_match_non_fy_columns(self, column_name):
        """Pattern should not match non-fiscal year column names."""
        assert FY_COLUMN_PATTERN.match(column_name) is None


class ConcreteClass(FiscalYearMixin):
    """Concrete class to test the mixin."""

    pass


class TestDetectFYColumn:
    """Test automatic fiscal year column detection."""

    def test_detects_fiscal_year_column(self):
        """Should detect 'Fiscal Year' column."""
        df = pd.DataFrame({"Fiscal Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        assert mixin._detect_fy_column(df) == "Fiscal Year"

    def test_detects_fy_column(self):
        """Should detect 'FY' column."""
        df = pd.DataFrame({"FY": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        assert mixin._detect_fy_column(df) == "FY"

    def test_detects_year_column(self):
        """Should detect 'Year' column."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        assert mixin._detect_fy_column(df) == "Year"

    def test_detects_fy_with_digits(self):
        """Should detect 'FY2024' column."""
        df = pd.DataFrame({"FY2024": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        assert mixin._detect_fy_column(df) == "FY2024"

    def test_returns_none_when_no_fy_column(self):
        """Should return None when no FY column is found."""
        df = pd.DataFrame({"Date": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        assert mixin._detect_fy_column(df) is None


class TestNormalizeFYColumn:
    """Test fiscal year column normalization."""

    def test_converts_valid_years_to_datetime(self):
        """Should convert 4-digit years to datetime objects."""
        df = pd.DataFrame({"Year": [2020, 2021, 2022]})
        mixin = ConcreteClass()
        result = mixin._normalize_fy_column(df, "Year")

        assert result["Year"].iloc[0] == datetime(2020, 1, 1)
        assert result["Year"].iloc[1] == datetime(2021, 1, 1)
        assert result["Year"].iloc[2] == datetime(2022, 1, 1)

    def test_preserves_1976_tq(self):
        """Should preserve '1976 TQ' as a string."""
        df = pd.DataFrame({"Year": ["1976 TQ", 1977, 1978]})
        mixin = ConcreteClass()
        result = mixin._normalize_fy_column(df, "Year")

        assert result["Year"].iloc[0] == "1976 TQ"
        assert result["Year"].iloc[1] == datetime(1977, 1, 1)
        assert result["Year"].iloc[2] == datetime(1978, 1, 1)

    def test_filters_non_numeric_values(self):
        """Should filter out non-numeric values like 'Totals'."""
        df = pd.DataFrame({"Year": [2020, 2021, "Totals"], "Amount": [100, 200, 300]})
        mixin = ConcreteClass()
        result = mixin._normalize_fy_column(df, "Year")

        assert len(result) == 2
        assert result["Year"].iloc[0] == datetime(2020, 1, 1)
        assert result["Year"].iloc[1] == datetime(2021, 1, 1)

    def test_handles_na_values(self):
        """Should handle NA values gracefully."""
        df = pd.DataFrame({"Year": [2020, None, 2022]})
        mixin = ConcreteClass()
        result = mixin._normalize_fy_column(df, "Year")

        assert len(result) == 2
        assert result["Year"].iloc[0] == datetime(2020, 1, 1)
        assert result["Year"].iloc[1] == datetime(2022, 1, 1)


class TestApplyFiscalYearConversion:
    """Test the main _apply_fiscal_year_conversion method."""

    def test_auto_detects_and_converts_fy_column(self):
        """Should auto-detect and convert fiscal year columns."""
        df = pd.DataFrame({"Fiscal Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        result = mixin._apply_fiscal_year_conversion(df)

        assert result["Fiscal Year"].iloc[0] == datetime(2020, 1, 1)
        assert result["Fiscal Year"].iloc[1] == datetime(2021, 1, 1)

    def test_uses_specified_column(self):
        """Should use the specified column when provided."""
        df = pd.DataFrame({"Budget Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        result = mixin._apply_fiscal_year_conversion(df, fiscal_year_column="Budget Year")

        assert result["Budget Year"].iloc[0] == datetime(2020, 1, 1)
        assert result["Budget Year"].iloc[1] == datetime(2021, 1, 1)

    def test_disabled_with_false(self):
        """Should skip conversion when fiscal_year_column=False."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        result = mixin._apply_fiscal_year_conversion(df, fiscal_year_column=False)

        # Values should remain as integers
        assert result["Year"].iloc[0] == 2020
        assert result["Year"].iloc[1] == 2021

    def test_returns_unchanged_when_no_fy_column_detected(self):
        """Should return unchanged DataFrame when no FY column detected."""
        df = pd.DataFrame({"Date": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()
        result = mixin._apply_fiscal_year_conversion(df)

        assert result["Date"].iloc[0] == 2020
        assert result["Date"].iloc[1] == 2021

    def test_warns_when_specified_column_not_found(self):
        """Should warn and return unchanged when specified column not found."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()

        with patch("tpsplots.data_sources.fiscal_year_mixin.logger") as mock_logger:
            result = mixin._apply_fiscal_year_conversion(df, fiscal_year_column="NonExistent")
            mock_logger.warning.assert_called_once()

        # Should return unchanged DataFrame
        assert result["Year"].iloc[0] == 2020
        assert result["Year"].iloc[1] == 2021


class TestGoogleSheetsFiscalYearIntegration:
    """Test FiscalYearMixin integration with GoogleSheetsSource."""

    def test_google_sheets_source_has_mixin(self):
        """GoogleSheetsSource should inherit from FiscalYearMixin."""
        from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

        assert issubclass(GoogleSheetsSource, FiscalYearMixin)

    def test_nasa_budget_has_mixin(self):
        """NASABudget should inherit from FiscalYearMixin."""
        from tpsplots.data_sources.nasa_budget_data_source import NASABudget

        assert issubclass(NASABudget, FiscalYearMixin)
