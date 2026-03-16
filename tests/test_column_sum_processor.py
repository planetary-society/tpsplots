"""Tests for ColumnSumProcessor."""

import pandas as pd
import pytest

from tpsplots.processors.column_sum_processor import ColumnSumConfig, ColumnSumProcessor


@pytest.fixture
def numeric_df():
    return pd.DataFrame(
        {
            "Fiscal Year": [2020, 2021, 2022],
            "Budget": [100.0, 200.0, 300.0],
            "Amount": [10.0, 20.0, 30.0],
        }
    )


# ── Auto-detect mode ──


class TestColumnSumProcessorAutoDetect:
    def test_sums_numeric_columns(self, numeric_df):
        result = ColumnSumProcessor(ColumnSumConfig()).process(numeric_df)
        sums = result.attrs["column_sums"]
        assert sums["Budget"] == 600.0
        assert sums["Amount"] == 60.0

    def test_skips_non_numeric(self):
        df = pd.DataFrame({"Label": ["a", "b"], "Value": [1.0, 2.0]})
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        sums = result.attrs["column_sums"]
        assert "Label" not in sums
        assert sums["Value"] == 3.0

    def test_skips_raw_columns(self):
        df = pd.DataFrame({"Budget": [100.0, 200.0], "Budget_raw": [100.0, 200.0]})
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        sums = result.attrs["column_sums"]
        assert "Budget_raw" not in sums
        assert sums["Budget"] == 300.0

    def test_exclude_list_respected(self, numeric_df):
        result = ColumnSumProcessor(ColumnSumConfig(exclude=["Fiscal Year"])).process(numeric_df)
        sums = result.attrs["column_sums"]
        assert "Fiscal Year" not in sums
        assert "Budget" in sums
        assert "Amount" in sums

    def test_nan_values_ignored(self):
        df = pd.DataFrame({"Value": [1.0, None, 3.0]})
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        assert result.attrs["column_sums"]["Value"] == 4.0

    def test_does_not_mutate_input(self, numeric_df):
        original_attrs = dict(numeric_df.attrs)
        original_cols = list(numeric_df.columns)
        ColumnSumProcessor(ColumnSumConfig()).process(numeric_df)
        assert list(numeric_df.columns) == original_cols
        assert numeric_df.attrs == original_attrs

    def test_attrs_key_is_column_sums(self, numeric_df):
        result = ColumnSumProcessor(ColumnSumConfig()).process(numeric_df)
        assert "column_sums" in result.attrs
        # No flat sum_* keys — only the single dict
        assert not any(str(k).startswith("sum_") for k in result.attrs)


# ── Explicit columns mode ──


class TestColumnSumProcessorExplicitColumns:
    def test_explicit_columns_override_autodetect(self):
        df = pd.DataFrame({"A": [1.0, 2.0], "B": [10.0, 20.0], "C": [100.0, 200.0]})
        result = ColumnSumProcessor(ColumnSumConfig(columns=["A"])).process(df)
        sums = result.attrs["column_sums"]
        assert list(sums.keys()) == ["A"]
        assert sums["A"] == 3.0

    def test_explicit_columns_ignores_exclude(self):
        df = pd.DataFrame({"A": [1.0, 2.0], "B": [10.0, 20.0]})
        # exclude is ignored when columns is set explicitly
        result = ColumnSumProcessor(ColumnSumConfig(columns=["A", "B"], exclude=["A"])).process(df)
        sums = result.attrs["column_sums"]
        assert "A" in sums
        assert "B" in sums

    def test_missing_explicit_column_skipped_gracefully(self):
        df = pd.DataFrame({"A": [1.0]})
        result = ColumnSumProcessor(ColumnSumConfig(columns=["A", "NonExistent"])).process(df)
        sums = result.attrs["column_sums"]
        assert "A" in sums
        assert "NonExistent" not in sums

    def test_non_numeric_explicit_column_skipped(self):
        df = pd.DataFrame({"Label": ["x", "y"], "Value": [5.0, 5.0]})
        result = ColumnSumProcessor(ColumnSumConfig(columns=["Label", "Value"])).process(df)
        sums = result.attrs["column_sums"]
        assert "Label" not in sums
        assert sums["Value"] == 10.0


# ── Edge cases ──


class TestColumnSumProcessorEmpty:
    def test_empty_dataframe_produces_empty_dict(self):
        df = pd.DataFrame()
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        assert result.attrs["column_sums"] == {}

    def test_no_numeric_columns_produces_empty_dict(self):
        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Label": ["x", "y"]})
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        assert result.attrs["column_sums"] == {}

    def test_sums_are_floats(self):
        df = pd.DataFrame({"Count": [1, 2, 3]})  # integer column
        result = ColumnSumProcessor(ColumnSumConfig()).process(df)
        total = result.attrs["column_sums"]["Count"]
        assert isinstance(total, float)
        assert total == 6.0
