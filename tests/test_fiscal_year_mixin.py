"""Tests for FiscalYearMixin functionality."""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tpsplots.data_sources.fiscal_year_mixin import (
    FY_COLUMN_PATTERN,
    TQ_LABEL_PATTERN,
    FiscalYearMixin,
)

NASA_AUTHORIZATIONS_CSV = (
    Path(__file__).resolve().parents[1] / "yaml" / "examples" / "data" / "nasa_authorizations.csv"
)


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
        """A TQ timeline should preserve every fiscal period as a label."""
        df = pd.DataFrame({"Year": [1976, "1976TQ", 1977, 1978]})
        mixin = ConcreteClass()
        result = mixin._normalize_fy_column(df, "Year")

        assert result["Year"].tolist() == ["1976", "1976 TQ", "1977", "1978"]
        # A mixed annual/TQ axis stays a string column (not datetime64). Pandas 3
        # infers the "str" StringDtype for text; pandas 2 uses "object". Assert the
        # string-ness rather than a version-specific dtype.
        assert pd.api.types.is_string_dtype(result["Year"])

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


class TestTQMask:
    """Anchored transition-quarter detection."""

    @pytest.mark.parametrize(
        "label",
        ["TQ", "1976TQ", "1976 TQ", "FY1976 TQ", "FY76 TQ", "  1976 TQ  ", "tq"],
    )
    def test_mask_accepts_transition_quarter_labels(self, label):
        assert TQ_LABEL_PATTERN.match(label)
        mask = FiscalYearMixin._tq_mask(pd.Series([label]))
        assert bool(mask.iloc[0]) is True

    @pytest.mark.parametrize(
        "label",
        ["not-tq-related", "Totals-TQE", "2020", "Totals", ""],
    )
    def test_mask_rejects_stray_tq_substrings(self, label):
        assert not TQ_LABEL_PATTERN.match(label)
        mask = FiscalYearMixin._tq_mask(pd.Series([label]))
        assert bool(mask.iloc[0]) is False

    def test_stray_tq_substring_row_is_dropped_not_relabeled(self):
        """A column with a stray "tq" substring still becomes a datetime axis;
        the invalid row is dropped, never mislabeled "1976 TQ"."""
        df = pd.DataFrame({"Year": ["2020", "2021", "not-tq-related"]})
        result = FiscalYearMixin._normalize_fy_column(df, "Year")

        assert pd.api.types.is_datetime64_any_dtype(result["Year"])
        assert len(result) == 2
        assert result["Year"].tolist() == [datetime(2020, 1, 1), datetime(2021, 1, 1)]


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

    def test_warns_when_specified_column_not_found(self, caplog):
        """Should warn and return unchanged when specified column not found."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        mixin = ConcreteClass()

        with caplog.at_level(logging.WARNING):
            result = mixin._apply_fiscal_year_conversion(df, fiscal_year_column="NonExistent")

        # Should return unchanged DataFrame
        assert result["Year"].iloc[0] == 2020
        assert result["Year"].iloc[1] == 2021
        warning_messages = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        assert any("NonExistent" in message for message in warning_messages)


class TestYearParseFraction:
    """The plausibility metric used to gate fiscal-year conversion."""

    def test_all_plausible_years(self):
        assert FiscalYearMixin._year_parse_fraction(pd.Series([2020, 2021, 2022])) == 1.0

    def test_float_years_are_plausible(self):
        assert FiscalYearMixin._year_parse_fraction(pd.Series([1958.0, 1959.0])) == 1.0

    def test_string_years_are_plausible(self):
        assert FiscalYearMixin._year_parse_fraction(pd.Series(["2020", "2021"])) == 1.0

    def test_transition_quarter_labels_count_as_plausible(self):
        frac = FiscalYearMixin._year_parse_fraction(pd.Series([1976, "1976TQ", 1977, 1978]))
        assert frac == 1.0

    def test_ids_and_fractions_are_not_plausible(self):
        # 100234 is out of [1900, 2100]; 0.1-0.9 are well below MIN_YEAR.
        assert FiscalYearMixin._year_parse_fraction(pd.Series([100234, 0.1, 0.5, 0.9])) == 0.0

    def test_nulls_excluded_from_denominator(self):
        frac = FiscalYearMixin._year_parse_fraction(pd.Series([2020, None, 2021, np.nan]))
        assert frac == 1.0

    def test_all_null_returns_one(self):
        assert FiscalYearMixin._year_parse_fraction(pd.Series([np.nan, np.nan])) == 1.0

    def test_float_dtype_column_never_raises(self):
        # A pure float64 column must not raise a str-accessor / regex type error.
        frac = FiscalYearMixin._year_parse_fraction(pd.Series([2020.0, 2021.0, 0.5]))
        assert 0.0 <= frac <= 1.0


class TestPlausibilityGate:
    """_apply_fiscal_year_conversion only converts columns that look like years."""

    def test_nasa_authorizations_csv_loads_and_year_converts(self):
        """Regression: the real CSV (junk columns + garbage rows + a numeric
        Year) loads without error and Year still becomes datetime64."""
        from tpsplots.data_sources.csv_source import CSVSource

        assert NASA_AUTHORIZATIONS_CSV.exists()
        df = CSVSource(csv_path=str(NASA_AUTHORIZATIONS_CSV)).data()

        assert pd.api.types.is_datetime64_any_dtype(df["Year"])
        assert df["Year"].iloc[0] == datetime(2022, 1, 1)
        # The junk header row ("Year" string) and blank rows are filtered out.
        assert df["Year"].notna().all()

    def test_mostly_non_year_column_is_left_unconverted_with_warning(self, caplog):
        """A column named 'Year' whose values are mostly IDs/fractions is left
        alone (no silent coercion or row loss) and a warning is logged."""
        df = pd.DataFrame({"Year": [100234.0, 100235.0, 0.5, 0.9, 0.1], "Amount": range(5)})
        mixin = ConcreteClass()

        with caplog.at_level(logging.WARNING):
            result = mixin._apply_fiscal_year_conversion(df)

        # Column untouched, no rows dropped.
        assert not pd.api.types.is_datetime64_any_dtype(result["Year"])
        assert result["Year"].tolist() == [100234.0, 100235.0, 0.5, 0.9, 0.1]
        assert len(result) == 5

        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("Year" in m and "fiscal_year_column" in m for m in warnings)

    def test_float_typed_real_years_still_convert(self):
        """A float-typed column of genuine years converts as before."""
        df = pd.DataFrame({"Year": [1958.0, 1959.0], "Amount": [1, 2]})
        mixin = ConcreteClass()

        result = mixin._apply_fiscal_year_conversion(df)

        assert result["Year"].iloc[0] == datetime(1958, 1, 1)
        assert result["Year"].iloc[1] == datetime(1959, 1, 1)

    def test_configured_non_year_column_is_left_unconverted_with_warning(self, caplog):
        """The plausibility gate also applies to an explicitly configured column."""
        df = pd.DataFrame({"Ident": [500123, 500124, 500125], "Amount": [1, 2, 3]})
        mixin = ConcreteClass()

        with caplog.at_level(logging.WARNING):
            result = mixin._apply_fiscal_year_conversion(df, fiscal_year_column="Ident")

        assert result["Ident"].tolist() == [500123, 500124, 500125]
        warnings = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert any("Ident" in m for m in warnings)


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
