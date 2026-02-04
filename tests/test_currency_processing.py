"""Tests for currency processing utilities."""

import pandas as pd
import pytest

from tpsplots.utils.currency_processing import (
    CURRENCY_DETECT_PATTERN,
    CURRENCY_RE,
    clean_currency_column,
    looks_like_currency_column,
)


class TestCurrencyDetectPattern:
    """Tests for the CURRENCY_DETECT_PATTERN regex."""

    @pytest.mark.parametrize(
        "value",
        [
            "$42,013",
            "$1,234.56",
            "$100",
            "$1,000,000",
            "$0",
            "$999.99",
        ],
    )
    def test_matches_valid_currency(self, value):
        """Pattern should match valid currency formats."""
        assert CURRENCY_DETECT_PATTERN.match(value) is not None

    @pytest.mark.parametrize(
        "value",
        [
            "42013",  # No dollar sign
            "Alice",  # Text
            "$abc",  # Invalid characters after $
            "100$",  # Dollar sign at end
            "$1,234.567",  # Too many decimal places
            "",  # Empty string
            "$",  # Just dollar sign
        ],
    )
    def test_rejects_invalid_currency(self, value):
        """Pattern should reject non-currency formats."""
        assert CURRENCY_DETECT_PATTERN.match(value) is None


class TestCurrencyCleaningPattern:
    """Tests for the CURRENCY_RE regex used in cleaning."""

    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [
            ("$42,013", "42013"),
            ("$1.5M", "1.5"),
            ("$2.5B", "2.5"),
            ("1,000", "1000"),
            ("$100", "100"),
        ],
    )
    def test_removes_currency_symbols(self, input_val, expected):
        """Pattern should remove $, commas, and M/B suffixes."""
        result = CURRENCY_RE.sub("", input_val)
        assert result == expected


class TestLooksLikeCurrencyColumn:
    """Tests for looks_like_currency_column function."""

    def test_detects_currency_column(self):
        """Should detect column with mostly currency values."""
        series = pd.Series(["$42,013", "$1,234.56", "$100", "$999.99"])
        assert looks_like_currency_column("Amount", series)

    def test_rejects_text_column(self):
        """Should reject column with text values."""
        series = pd.Series(["Alice", "Bob", "Charlie", "Diana"])
        assert not looks_like_currency_column("Name", series)

    def test_rejects_plain_numbers(self):
        """Should reject column with plain numbers (no $ sign)."""
        series = pd.Series(["100", "200", "300", "400"])
        assert not looks_like_currency_column("Count", series)

    def test_handles_mixed_content_above_threshold(self):
        """Should detect if 80%+ values match currency pattern."""
        # 4/5 = 80% match
        series = pd.Series(["$100", "$200", "$300", "$400", "N/A"])
        assert looks_like_currency_column("Amount", series)

    def test_rejects_mixed_content_below_threshold(self):
        """Should reject if <80% values match currency pattern."""
        # 3/5 = 60% match
        series = pd.Series(["$100", "$200", "$300", "N/A", "Unknown"])
        assert not looks_like_currency_column("Amount", series)

    def test_respects_custom_threshold(self):
        """Should use custom threshold when provided."""
        # 3/5 = 60% match, passes with 0.5 threshold
        series = pd.Series(["$100", "$200", "$300", "N/A", "Unknown"])
        assert looks_like_currency_column("Amount", series, threshold=0.5)

    def test_requires_minimum_samples(self):
        """Should require minimum number of samples."""
        series = pd.Series(["$100", "$200"])  # Only 2 samples
        assert not looks_like_currency_column("Amount", series)
        assert looks_like_currency_column("Amount", series, min_samples=2)

    def test_handles_empty_series(self):
        """Should return False for empty series."""
        series = pd.Series([], dtype=object)
        assert not looks_like_currency_column("Amount", series)

    def test_handles_all_null_series(self):
        """Should return False for all-null series."""
        series = pd.Series([None, None, None])
        assert not looks_like_currency_column("Amount", series)


class TestCleanCurrencyColumn:
    """Tests for clean_currency_column function."""

    def test_cleans_basic_currency(self):
        """Should clean basic currency values."""
        series = pd.Series(["$42,013", "$1,234.56"])
        result = clean_currency_column(series)
        assert result.iloc[0] == 42013.0
        assert result.iloc[1] == 1234.56

    def test_returns_float64(self):
        """Should return float64 dtype."""
        series = pd.Series(["$100", "$200"])
        result = clean_currency_column(series)
        assert result.dtype == "float64"

    def test_handles_na_values(self):
        """Should convert invalid values to NaN."""
        series = pd.Series(["$100", "", None, "N/A"])
        result = clean_currency_column(series)
        assert result.iloc[0] == 100.0
        assert pd.isna(result.iloc[1])
        assert pd.isna(result.iloc[2])
        assert pd.isna(result.iloc[3])

    def test_applies_multiplier(self):
        """Should apply multiplier to cleaned values."""
        series = pd.Series(["$1.5", "$2.0"])
        result = clean_currency_column(series, multiplier=1_000_000)
        assert result.iloc[0] == 1_500_000.0
        assert result.iloc[1] == 2_000_000.0

    def test_handles_m_suffix(self):
        """Should remove M suffix (millions)."""
        series = pd.Series(["$1.5M", "$2.5M"])
        result = clean_currency_column(series)
        assert result.iloc[0] == 1.5
        assert result.iloc[1] == 2.5

    def test_handles_b_suffix(self):
        """Should remove B suffix (billions)."""
        series = pd.Series(["$1.5B", "$2.5B"])
        result = clean_currency_column(series)
        assert result.iloc[0] == 1.5
        assert result.iloc[1] == 2.5

    def test_m_suffix_with_multiplier(self):
        """Should apply multiplier after removing M suffix."""
        # This simulates NASA budget data where values are in millions
        series = pd.Series(["$1.5M"])
        result = clean_currency_column(series, multiplier=1_000_000)
        assert result.iloc[0] == 1_500_000.0


class TestIntegrationWithGoogleSheetsSource:
    """Integration tests for currency cleaning in GoogleSheetsSource."""

    def test_auto_clean_creates_raw_column(self):
        """Auto-cleaning should preserve original in _raw column."""
        from unittest.mock import patch

        from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

        # Mock the CSV fetch to return test data - quote values with commas
        csv_data = 'Name,Amount\nAlice,"$42,013"\nBob,"$1,234.56"\nCharlie,$100\n'

        with patch.object(GoogleSheetsSource, "_fetch_csv_content", return_value=csv_data):
            source = GoogleSheetsSource(url="https://example.com/test")
            df = source.data()

        # Should have Amount as float64 and Amount_raw as original strings
        assert "Amount" in df.columns
        assert "Amount_raw" in df.columns
        assert df["Amount"].dtype == "float64"
        assert df["Amount"].iloc[0] == 42013.0
        assert df["Amount_raw"].iloc[0] == "$42,013"

    def test_auto_clean_can_be_disabled(self):
        """Auto-cleaning can be disabled with parameter."""
        from unittest.mock import patch

        from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

        # Quote values with commas
        csv_data = 'Name,Amount\nAlice,"$42,013"\nBob,"$1,234.56"\nCharlie,$100\n'

        with patch.object(GoogleSheetsSource, "_fetch_csv_content", return_value=csv_data):
            source = GoogleSheetsSource(url="https://example.com/test", auto_clean_currency=False)
            df = source.data()

        # Should NOT have _raw column, and Amount should be original strings
        assert "Amount" in df.columns
        assert "Amount_raw" not in df.columns
        assert df["Amount"].iloc[0] == "$42,013"

    def test_skips_non_currency_columns(self):
        """Should not clean columns that don't look like currency."""
        from unittest.mock import patch

        from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource

        csv_data = "Name,Count\nAlice,100\nBob,200\nCharlie,300\n"

        with patch.object(GoogleSheetsSource, "_fetch_csv_content", return_value=csv_data):
            source = GoogleSheetsSource(url="https://example.com/test")
            df = source.data()

        # Count should remain as-is (no _raw column)
        assert "Count" in df.columns
        assert "Count_raw" not in df.columns
