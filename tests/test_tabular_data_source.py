"""Tests for TabularDataSource pipeline in isolation.

Uses an InMemorySource stub that returns a fixed DataFrame from _read_raw_df(),
allowing the full processing pipeline to be tested without file I/O.
"""

import logging
from typing import ClassVar

import pandas as pd
import pytest

from tpsplots.data_sources.tabular_data_source import TabularDataSource

# ---------------------------------------------------------------------------
# Stub: concrete subclass that returns a fixed DataFrame
# ---------------------------------------------------------------------------


class InMemorySource(TabularDataSource):
    """Concrete TabularDataSource backed by an in-memory DataFrame."""

    def __init__(self, df: pd.DataFrame, **kwargs) -> None:
        self._raw_df = df
        super().__init__(**kwargs)

    def _read_raw_df(self) -> pd.DataFrame:
        return self._raw_df.copy()


# ---------------------------------------------------------------------------
# Test: Abstract enforcement
# ---------------------------------------------------------------------------


class TestAbstractEnforcement:
    """TabularDataSource cannot be instantiated directly."""

    def test_cannot_instantiate_abstract_class(self):
        """Attempting to instantiate TabularDataSource raises TypeError."""
        with pytest.raises(TypeError, match="abstract"):
            TabularDataSource()


# ---------------------------------------------------------------------------
# Test: Pipeline ordering
# ---------------------------------------------------------------------------


class TestPipelineOrdering:
    """Verify that the pipeline stages run in the documented order:
    column selection -> renaming -> cast -> currency -> FY conversion.
    """

    def test_rename_after_column_selection(self):
        """Renaming uses original column names (before rename), and column
        selection also uses original names."""
        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        source = InMemorySource(df, columns=["A", "B"], renames={"B": "Beta"})
        result = source.data()

        assert list(result.columns) == ["A", "Beta"]
        assert "C" not in result.columns

    def test_cast_applies_after_rename(self):
        """Cast refers to the *renamed* column names."""
        df = pd.DataFrame({"old_col": ["100", "200"]})
        source = InMemorySource(
            df,
            renames={"old_col": "Amount"},
            cast={"Amount": "int"},
        )
        result = source.data()

        assert result["Amount"].dtype == "int64"
        assert list(result["Amount"]) == [100, 200]

    def test_currency_cleaning_after_cast(self):
        """Currency cleaning runs on columns that survived cast.
        A column cast to int should not trigger currency cleaning."""
        df = pd.DataFrame(
            {
                "Price": ["$100", "$200", "$300", "$400"],
                "Year": [2020, 2021, 2022, 2023],
            }
        )
        source = InMemorySource(df, auto_clean_currency=True)
        result = source.data()

        # Price should have been cleaned to float
        assert result["Price"].dtype == "float64"
        assert "Price_raw" in result.columns

    def test_fy_conversion_runs_last(self):
        """Fiscal year conversion is the final pipeline step."""
        df = pd.DataFrame(
            {
                "Year": [2020, 2021, 2022],
                "Budget": ["$100", "$200", "$300"],
            }
        )
        # Disable currency cleaning so Budget stays as object
        source = InMemorySource(df, auto_clean_currency=False)
        result = source.data()

        # Year should be converted to datetime by FY auto-detection
        assert pd.api.types.is_datetime64_any_dtype(result["Year"])


# ---------------------------------------------------------------------------
# Test: TYPE_MAPPING and casting
# ---------------------------------------------------------------------------


class TestCastingWithTypeMapping:
    """TYPE_MAPPING resolves friendly names to pandas dtypes."""

    def test_cast_int(self):
        """'int' maps to int64."""
        df = pd.DataFrame({"col": ["10", "20", "30"]})
        source = InMemorySource(df, cast={"col": "int"}, fiscal_year_column=False)
        result = source.data()
        assert result["col"].dtype == "int64"
        assert list(result["col"]) == [10, 20, 30]

    def test_cast_float(self):
        """'float' maps to float64."""
        df = pd.DataFrame({"col": ["1.1", "2.2", "3.3"]})
        source = InMemorySource(df, cast={"col": "float"}, fiscal_year_column=False)
        result = source.data()
        assert result["col"].dtype == "float64"

    def test_cast_str(self):
        """'str' cast is non-coercive and preserves row values."""
        df = pd.DataFrame({"col": [1, 2, 3]})
        source = InMemorySource(df, cast={"col": "str"}, fiscal_year_column=False)
        result = source.data()
        assert list(result["col"]) == [1, 2, 3]

    def test_cast_datetime(self):
        """'datetime' maps to datetime64[ns]."""
        df = pd.DataFrame({"col": ["2020-01-01", "2021-06-15"]})
        source = InMemorySource(df, cast={"col": "datetime"}, fiscal_year_column=False)
        result = source.data()
        assert pd.api.types.is_datetime64_any_dtype(result["col"])

    def test_cast_int64_alias(self):
        """'int64' works the same as 'int'."""
        df = pd.DataFrame({"col": ["10", "20", "Invalid"]})
        source = InMemorySource(df, cast={"col": "int64"}, fiscal_year_column=False)
        result = source.data()
        assert len(result) == 2
        assert result["col"].dtype == "int64"

    def test_cast_float64_alias(self):
        """'float64' works the same as 'float'."""
        df = pd.DataFrame({"col": ["1.5", "N/A"]})
        source = InMemorySource(df, cast={"col": "float64"}, fiscal_year_column=False)
        result = source.data()
        assert len(result) == 1
        assert result["col"].dtype == "float64"


# ---------------------------------------------------------------------------
# Test: NaN row filtering
# ---------------------------------------------------------------------------


class TestNanRowFiltering:
    """Casting to a numeric type drops rows with non-numeric values."""

    def test_int_cast_drops_totals_row(self):
        """Rows like 'Totals' are dropped when casting to int."""
        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Totals"],
                "Amount": [100, 200, 300],
            }
        )
        source = InMemorySource(df, cast={"Year": "int"}, fiscal_year_column=False)
        result = source.data()

        assert len(result) == 2
        assert "Totals" not in result["Year"].values

    def test_float_cast_drops_non_numeric(self):
        """Non-numeric values are dropped when casting to float."""
        df = pd.DataFrame(
            {
                "Value": ["1.5", "2.5", "N/A"],
            }
        )
        source = InMemorySource(df, cast={"Value": "float"}, fiscal_year_column=False)
        result = source.data()

        assert len(result) == 2
        assert list(result["Value"]) == [1.5, 2.5]

    def test_dropped_rows_logged(self, caplog):
        """Dropped rows are logged at INFO level."""
        caplog.set_level(logging.INFO)
        df = pd.DataFrame({"Year": ["2020", "Totals"]})
        source = InMemorySource(df, cast={"Year": "int"}, fiscal_year_column=False)
        source.data()

        info_messages = [record.message for record in caplog.records if record.levelname == "INFO"]
        assert any("Dropped" in message and "Year" in message for message in info_messages)


# ---------------------------------------------------------------------------
# Test: Currency cleaning
# ---------------------------------------------------------------------------


class TestCurrencyCleaning:
    """Auto-detection and cleaning of currency columns."""

    def test_currency_enabled_by_default(self):
        """Currency cleaning is on by default."""
        df = pd.DataFrame(
            {
                "Amount": ["$1,000", "$2,000", "$3,000", "$4,000"],
            }
        )
        source = InMemorySource(df, fiscal_year_column=False)
        result = source.data()

        assert result["Amount"].dtype == "float64"
        assert "Amount_raw" in result.columns
        assert result["Amount_raw"].iloc[0] == "$1,000"

    def test_currency_disabled(self):
        """Currency cleaning can be disabled."""
        df = pd.DataFrame(
            {
                "Amount": ["$1,000", "$2,000", "$3,000", "$4,000"],
            }
        )
        source = InMemorySource(df, auto_clean_currency=False, fiscal_year_column=False)
        result = source.data()

        # Should remain as original strings
        assert result["Amount"].iloc[0] == "$1,000"
        assert "Amount_raw" not in result.columns

    def test_currency_with_multiplier(self):
        """Dict config with multiplier scales cleaned values."""
        df = pd.DataFrame(
            {
                "Budget": ["$1.5", "$2.0", "$3.0", "$4.0"],
            }
        )
        source = InMemorySource(
            df,
            auto_clean_currency={"enabled": True, "multiplier": 1_000_000},
            fiscal_year_column=False,
        )
        result = source.data()

        assert result["Budget"].dtype == "float64"
        assert result["Budget"].iloc[0] == 1_500_000.0

    def test_raw_column_preserved(self):
        """Original values are preserved in {column}_raw."""
        df = pd.DataFrame(
            {
                "Cost": ["$42,013", "$1,234.56", "$100", "$999.99"],
            }
        )
        source = InMemorySource(df, fiscal_year_column=False)
        result = source.data()

        assert "Cost_raw" in result.columns
        assert result["Cost_raw"].iloc[0] == "$42,013"

    def test_non_currency_columns_untouched(self):
        """Columns that don't look like currency are left alone."""
        df = pd.DataFrame(
            {
                "Name": ["Alice", "Bob", "Charlie", "Diana"],
            }
        )
        source = InMemorySource(df, fiscal_year_column=False)
        result = source.data()

        assert "Name_raw" not in result.columns
        assert pd.api.types.is_string_dtype(result["Name"])

    def test_class_attribute_auto_clean_currency_false(self):
        """Class-level AUTO_CLEAN_CURRENCY=False disables cleaning."""

        class NoCurrencySource(InMemorySource):
            AUTO_CLEAN_CURRENCY: ClassVar[bool] = False

        df = pd.DataFrame(
            {
                "Amount": ["$1,000", "$2,000", "$3,000", "$4,000"],
            }
        )
        source = NoCurrencySource(df, fiscal_year_column=False)
        result = source.data()

        assert result["Amount"].iloc[0] == "$1,000"
        assert "Amount_raw" not in result.columns


# ---------------------------------------------------------------------------
# Test: data() returns deep copy
# ---------------------------------------------------------------------------


class TestDeepCopy:
    """data() returns a deep copy so mutations don't affect internal state."""

    def test_modifying_returned_df_does_not_affect_source(self):
        """Mutating the returned DataFrame has no effect on subsequent calls."""
        df = pd.DataFrame({"A": [1, 2, 3]})
        source = InMemorySource(df, fiscal_year_column=False)

        first = source.data()
        first["A"] = [99, 99, 99]

        second = source.data()
        assert list(second["A"]) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Test: columns() returns column names
# ---------------------------------------------------------------------------


class TestColumnsMethod:
    """columns() returns a list of column names."""

    def test_returns_column_names(self):
        df = pd.DataFrame({"X": [1], "Y": [2], "Z": [3]})
        source = InMemorySource(df, fiscal_year_column=False)
        assert source.columns() == ["X", "Y", "Z"]

    def test_reflects_renames(self):
        df = pd.DataFrame({"old": [1]})
        source = InMemorySource(df, renames={"old": "new"}, fiscal_year_column=False)
        assert source.columns() == ["new"]


# ---------------------------------------------------------------------------
# Test: __getattr__ attribute access
# ---------------------------------------------------------------------------


class TestGetattr:
    """Attribute-style access to DataFrame columns."""

    def test_exact_match(self):
        """Exact column name works as attribute."""
        df = pd.DataFrame({"Amount": [10, 20]})
        source = InMemorySource(df, fiscal_year_column=False)
        assert source.Amount == [10, 20]

    def test_normalized_match(self):
        """snake_case attribute resolves to Title Case column."""
        df = pd.DataFrame({"Award Date": ["2020-01-01", "2021-06-15"]})
        source = InMemorySource(df, fiscal_year_column=False)
        assert source.award_date == ["2020-01-01", "2021-06-15"]

    def test_case_insensitive_match(self):
        """Case-insensitive fallback works."""
        df = pd.DataFrame({"amount": [10, 20]})
        source = InMemorySource(df, fiscal_year_column=False)
        assert source.Amount == [10, 20]

    def test_missing_attribute_raises(self):
        """Missing attribute raises AttributeError with class name."""
        df = pd.DataFrame({"A": [1]})
        source = InMemorySource(df, fiscal_year_column=False)
        with pytest.raises(AttributeError, match="InMemorySource"):
            _ = source.nonexistent


# ---------------------------------------------------------------------------
# Test: Class vs instance attribute precedence
# ---------------------------------------------------------------------------


class TestClassVsInstancePrecedence:
    """Instance constructor arguments override class-level attributes."""

    def test_instance_cast_overrides_class_cast(self):
        """Instance _cast takes priority over class CAST."""

        class TypedSource(InMemorySource):
            CAST: ClassVar[dict[str, str]] = {"Year": "str"}

        df = pd.DataFrame({"Year": ["2020", "2021", "Totals"]})
        # Instance says int, class says str -> int wins, "Totals" dropped
        source = TypedSource(df, cast={"Year": "int"}, fiscal_year_column=False)
        result = source.data()

        assert len(result) == 2
        assert result["Year"].dtype == "int64"

    def test_class_cast_used_when_no_instance_cast(self):
        """Class CAST is used when instance _cast is None."""

        class TypedSource(InMemorySource):
            CAST: ClassVar[dict[str, str]] = {"Year": "int"}

        df = pd.DataFrame({"Year": ["2020", "2021", "Totals"]})
        source = TypedSource(df, fiscal_year_column=False)
        result = source.data()

        assert len(result) == 2
        assert result["Year"].dtype == "int64"

    def test_instance_columns_overrides_class_columns(self):
        """Instance _columns takes priority over class COLUMNS."""

        class FilteredSource(InMemorySource):
            COLUMNS: ClassVar[list[str]] = ["A", "B"]

        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        source = FilteredSource(df, columns=["A", "C"], fiscal_year_column=False)
        result = source.data()

        assert list(result.columns) == ["A", "C"]

    def test_instance_renames_overrides_class_renames(self):
        """Instance _renames takes priority over class RENAMES."""

        class RenamedSource(InMemorySource):
            RENAMES: ClassVar[dict[str, str]] = {"A": "Alpha"}

        df = pd.DataFrame({"A": [1]})
        source = RenamedSource(df, renames={"A": "Aardvark"}, fiscal_year_column=False)
        result = source.data()

        assert "Aardvark" in result.columns
        assert "Alpha" not in result.columns


# ---------------------------------------------------------------------------
# Test: fiscal_year_column parameter
# ---------------------------------------------------------------------------


class TestFiscalYearColumn:
    """fiscal_year_column: None=auto-detect, str=specific column, False=disable."""

    def test_auto_detect_fiscal_year(self):
        """None (default) auto-detects 'Year' column and converts to datetime."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        source = InMemorySource(df)
        result = source.data()

        assert pd.api.types.is_datetime64_any_dtype(result["Year"])

    def test_auto_detect_fiscal_year_column_name(self):
        """Auto-detects 'Fiscal Year' column."""
        df = pd.DataFrame({"Fiscal Year": [2020, 2021], "Amount": [100, 200]})
        source = InMemorySource(df)
        result = source.data()

        assert pd.api.types.is_datetime64_any_dtype(result["Fiscal Year"])

    def test_specific_column_name(self):
        """String value specifies which column to convert."""
        df = pd.DataFrame(
            {
                "Budget Year": [2020, 2021],
                "Year": [1, 2],
                "Amount": [100, 200],
            }
        )
        source = InMemorySource(df, fiscal_year_column="Budget Year")
        result = source.data()

        # Budget Year should be datetime, not the auto-detected Year
        assert pd.api.types.is_datetime64_any_dtype(result["Budget Year"])
        # "Year" would have been auto-detected, but we specified Budget Year
        # Year column should remain numeric because FY conversion only targets one col
        assert not pd.api.types.is_datetime64_any_dtype(result["Year"])

    def test_disabled_with_false(self):
        """False disables FY conversion entirely."""
        df = pd.DataFrame({"Year": [2020, 2021], "Amount": [100, 200]})
        source = InMemorySource(df, fiscal_year_column=False)
        result = source.data()

        # Year should remain as integer, not converted to datetime
        assert result["Year"].iloc[0] == 2020
        assert not pd.api.types.is_datetime64_any_dtype(result["Year"])

    def test_no_fy_column_returns_unchanged(self):
        """When no FY column is detected, DataFrame is unchanged."""
        df = pd.DataFrame({"Date": ["2020-01-01"], "Amount": [100]})
        source = InMemorySource(df)
        result = source.data()

        # "Date" does not match FY pattern, so no conversion
        assert result["Date"].iloc[0] == "2020-01-01"
