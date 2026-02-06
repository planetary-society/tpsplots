"""Tests for GoogleSheetsSource data loading and transformations."""

from typing import ClassVar

import pandas as pd

from tpsplots.data_sources.google_sheets_source import GoogleSheetsSource


class TestGoogleSheetsSourceCasting:
    """Tests for GoogleSheetsSource._cast_columns numeric coercion behavior."""

    def test_cast_int_filters_non_numeric_rows(self):
        """Test that casting to int filters out rows with non-numeric values."""
        # Create a source with mock data containing a summary row
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "2022", "Totals"],
                "Amount": [100, 200, 300, 600],
            }
        )

        result = source._cast_columns(df)

        # The "Totals" row should be dropped
        assert len(result) == 3
        assert "Totals" not in result["Year"].values
        assert list(result["Year"]) == [2020, 2021, 2022]
        assert result["Year"].dtype == "int64"

    def test_cast_float_filters_non_numeric_rows(self):
        """Test that casting to float filters out rows with non-numeric values."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Value": "float"}

        df = pd.DataFrame(
            {
                "Category": ["A", "B", "C", "Total"],
                "Value": ["1.5", "2.5", "3.5", "N/A"],
            }
        )

        result = source._cast_columns(df)

        assert len(result) == 3
        assert list(result["Value"]) == [1.5, 2.5, 3.5]
        assert result["Value"].dtype == "float64"

    def test_cast_datetime_filters_invalid_dates(self):
        """Test that casting to datetime filters out rows with invalid dates."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Date": "datetime"}

        df = pd.DataFrame(
            {
                "Date": ["2020-01-01", "2021-06-15", "Invalid Date"],
                "Amount": [100, 200, 300],
            }
        )

        result = source._cast_columns(df)

        assert len(result) == 2
        assert pd.api.types.is_datetime64_any_dtype(result["Date"])

    def test_cast_str_does_not_filter_rows(self):
        """Test that casting to string does not filter any rows."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"ID": "str"}

        df = pd.DataFrame(
            {
                "ID": [123, 456, 789],
                "Name": ["A", "B", "C"],
            }
        )

        result = source._cast_columns(df)

        # No rows should be dropped
        assert len(result) == 3
        assert result["ID"].dtype == "object"

    def test_cast_multiple_columns(self):
        """Test casting multiple columns with different types."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int", "Amount": "float"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Summary"],
                "Amount": ["100.5", "200.5", "Total"],
            }
        )

        result = source._cast_columns(df)

        # Both columns have invalid values in row 3, so it should be dropped
        assert len(result) == 2
        assert result["Year"].dtype == "int64"
        assert result["Amount"].dtype == "float64"

    def test_cast_preserves_valid_rows_with_nan_in_other_columns(self):
        """Test that rows are only dropped if the CAST column has invalid values."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "2022"],
                "Optional": [100, None, 300],  # NaN in non-cast column
            }
        )

        result = source._cast_columns(df)

        # All rows should be preserved - only Year column is checked
        assert len(result) == 3

    def test_cast_no_rows_dropped_when_all_valid(self):
        """Test that no rows are dropped when all values are valid."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "2022"],
                "Amount": [100, 200, 300],
            }
        )

        result = source._cast_columns(df)

        assert len(result) == 3
        assert result["Year"].dtype == "int64"

    def test_cast_empty_dict_returns_unchanged(self):
        """Test that empty cast dict returns DataFrame unchanged."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {}

        df = pd.DataFrame({"A": [1, 2, 3]})
        original_len = len(df)

        result = source._cast_columns(df)

        assert len(result) == original_len

    def test_cast_none_returns_unchanged(self):
        """Test that None cast returns DataFrame unchanged."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = None

        df = pd.DataFrame({"A": [1, 2, 3]})
        original_len = len(df)

        result = source._cast_columns(df)

        assert len(result) == original_len

    def test_cast_missing_column_warns(self, caplog):
        """Test that casting a non-existent column logs a warning."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"NonExistent": "int"}

        df = pd.DataFrame({"A": [1, 2, 3]})

        result = source._cast_columns(df)

        assert "CAST column 'NonExistent' not found" in caplog.text
        assert len(result) == 3  # No rows dropped

    def test_cast_int64_type_mapping(self):
        """Test that 'int64' type string works the same as 'int'."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int64"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Invalid"],
            }
        )

        result = source._cast_columns(df)

        assert len(result) == 2
        assert result["Year"].dtype == "int64"

    def test_cast_float64_type_mapping(self):
        """Test that 'float64' type string works the same as 'float'."""
        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Value": "float64"}

        df = pd.DataFrame(
            {
                "Value": ["1.5", "2.5", "N/A"],
            }
        )

        result = source._cast_columns(df)

        assert len(result) == 2
        assert result["Value"].dtype == "float64"

    def test_cast_logs_dropped_rows(self, caplog):
        """Test that dropped rows are logged."""
        import logging

        caplog.set_level(logging.INFO)

        source = GoogleSheetsSource.__new__(GoogleSheetsSource)
        source._cast = {"Year": "int"}

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Totals", "Grand Total"],
            }
        )

        source._cast_columns(df)

        assert "Dropped 2 rows with invalid values" in caplog.text


class TestGoogleSheetsSourceClassAttribute:
    """Tests for GoogleSheetsSource with class-level CAST attribute."""

    def test_class_cast_attribute_used_when_no_instance_cast(self):
        """Test that class CAST attribute is used when instance _cast is None."""

        class TestSource(GoogleSheetsSource):
            URL = "https://example.com/test.csv"
            CAST: ClassVar[dict[str, str]] = {"Year": "int"}

        # Create instance without passing cast parameter
        source = TestSource.__new__(TestSource)
        source._cast = None  # Instance attribute is None

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Totals"],
            }
        )

        result = source._cast_columns(df)

        # Should use class CAST and filter out "Totals"
        assert len(result) == 2

    def test_instance_cast_overrides_class_cast(self):
        """Test that instance _cast overrides class CAST attribute."""

        class TestSource(GoogleSheetsSource):
            URL = "https://example.com/test.csv"
            CAST: ClassVar[dict[str, str]] = {"Year": "str"}  # Class says string

        source = TestSource.__new__(TestSource)
        source._cast = {"Year": "int"}  # Instance says int

        df = pd.DataFrame(
            {
                "Year": ["2020", "2021", "Totals"],
            }
        )

        result = source._cast_columns(df)

        # Should use instance _cast (int) and filter out "Totals"
        assert len(result) == 2
        assert result["Year"].dtype == "int64"
