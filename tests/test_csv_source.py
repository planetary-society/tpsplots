"""Tests for CSVSource with temp CSV files."""

from datetime import datetime

import pandas as pd
import pytest

from tpsplots.data_sources.csv_source import CSVSource


class TestCSVSourceBasicReading:
    """Basic CSV reading tests."""

    def test_reads_csv_file(self, tmp_path):
        """Creates a CSV, reads it back via CSVSource."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name,Value\nAlice,10\nBob,20\n")

        source = CSVSource(csv_path=str(csv_file), fiscal_year_column=False)
        df = source.data()

        assert len(df) == 2
        assert list(df.columns) == ["Name", "Value"]
        assert list(df["Name"]) == ["Alice", "Bob"]

    def test_returns_dataframe(self, tmp_path):
        """data() returns a pandas DataFrame."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("A,B\n1,2\n")

        source = CSVSource(csv_path=str(csv_file), fiscal_year_column=False)
        result = source.data()
        assert isinstance(result, pd.DataFrame)

    def test_default_truncate_at_removes_total_colon_and_trailing_rows(self, tmp_path):
        """Default truncate_at should drop 'Total:' row and everything after it."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Label,Value\nA,1\nB,2\nTotal:,3\nC,4\n")

        source = CSVSource(csv_path=str(csv_file), fiscal_year_column=False)
        df = source.data()

        assert list(df["Label"]) == ["A", "B"]

    def test_truncate_at_false_preserves_total_rows(self, tmp_path):
        """truncate_at=False should preserve total rows and trailing data."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Label,Value\nA,1\nB,2\nTotal:,3\nC,4\n")

        source = CSVSource(csv_path=str(csv_file), truncate_at=False, fiscal_year_column=False)
        df = source.data()

        assert list(df["Label"]) == ["A", "B", "Total:", "C"]

    def test_truncate_at_custom_marker_uses_exact_match(self, tmp_path):
        """Custom truncate_at should match the provided marker exactly."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Label,Value\nA,1\nTotals,2\nC,3\n")

        source = CSVSource(csv_path=str(csv_file), truncate_at="Totals", fiscal_year_column=False)
        df = source.data()

        assert list(df["Label"]) == ["A"]

    def test_default_truncate_at_does_not_match_other_summary_labels(self, tmp_path):
        """Default 'Total:' truncation should not match different labels like 'Totals'."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Label,Value\nA,1\nTotals,2\nC,3\n")

        source = CSVSource(csv_path=str(csv_file), fiscal_year_column=False)
        df = source.data()

        assert list(df["Label"]) == ["A", "Totals", "C"]


class TestCSVSourceMissingPath:
    """Error handling for missing/invalid paths."""

    def test_missing_path_raises_value_error(self):
        """CSVSource without csv_path raises ValueError."""
        with pytest.raises(ValueError, match="requires a csv_path"):
            CSVSource(csv_path=None)

    def test_empty_string_path_raises_value_error(self):
        """CSVSource with empty string raises ValueError."""
        with pytest.raises(ValueError, match="requires a csv_path"):
            CSVSource(csv_path="")


class TestCSVSourceAllParams:
    """All TabularDataSource params are forwarded and applied."""

    def test_cast_applied(self, tmp_path):
        """Non-numeric cast does not drop rows or rewrite values."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("ID,Score\n1,10.5\n2,20.5\n3,30.5\n")

        source = CSVSource(
            csv_path=str(csv_file),
            cast={"ID": "str"},
            fiscal_year_column=False,
        )
        df = source.data()

        assert len(df) == 3
        assert list(df["ID"]) == [1, 2, 3]

    def test_columns_applied(self, tmp_path):
        """columns parameter selects specific columns."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("A,B,C\n1,2,3\n4,5,6\n")

        source = CSVSource(
            csv_path=str(csv_file),
            columns=["A", "C"],
            fiscal_year_column=False,
        )
        df = source.data()

        assert list(df.columns) == ["A", "C"]

    def test_renames_applied(self, tmp_path):
        """renames parameter renames columns."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("old_name,value\nfoo,1\nbar,2\n")

        source = CSVSource(
            csv_path=str(csv_file),
            renames={"old_name": "new_name"},
            fiscal_year_column=False,
        )
        df = source.data()

        assert "new_name" in df.columns
        assert "old_name" not in df.columns

    def test_auto_clean_currency_applied(self, tmp_path):
        """auto_clean_currency cleans dollar-formatted columns."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text('Name,Cost\nA,"$1,000"\nB,"$2,000"\nC,"$3,000"\nD,"$4,000"\n')

        source = CSVSource(
            csv_path=str(csv_file),
            auto_clean_currency=True,
            fiscal_year_column=False,
        )
        df = source.data()

        assert df["Cost"].dtype == "float64"
        assert df["Cost"].iloc[0] == 1000.0
        assert "Cost_raw" in df.columns

    def test_auto_clean_currency_disabled(self, tmp_path):
        """auto_clean_currency=False preserves original strings."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text('Name,Cost\nA,"$1,000"\nB,"$2,000"\nC,"$3,000"\nD,"$4,000"\n')

        source = CSVSource(
            csv_path=str(csv_file),
            auto_clean_currency=False,
            fiscal_year_column=False,
        )
        df = source.data()

        assert df["Cost"].iloc[0] == "$1,000"
        assert "Cost_raw" not in df.columns

    def test_fiscal_year_column_applied(self, tmp_path):
        """fiscal_year_column parameter is forwarded to pipeline."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Budget Year,Amount\n2020,100\n2021,200\n")

        source = CSVSource(
            csv_path=str(csv_file),
            fiscal_year_column="Budget Year",
        )
        df = source.data()

        assert pd.api.types.is_datetime64_any_dtype(df["Budget Year"])

    def test_all_params_together(self, tmp_path):
        """All params work correctly in combination."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(
            "FY,Name,Budget,Extra\n"
            '2020,Alpha,"$1,000",x\n'
            '2021,Beta,"$2,000",y\n'
            '2022,Gamma,"$3,000",z\n'
            'Totals,Total,"$6,000",t\n'
        )

        source = CSVSource(
            csv_path=str(csv_file),
            columns=["FY", "Name", "Budget"],
            renames={"Name": "Mission"},
            cast={"FY": "int"},
            auto_clean_currency=True,
            fiscal_year_column=False,
        )
        df = source.data()

        # "Extra" column dropped by columns selection
        assert "Extra" not in df.columns
        # "Name" renamed to "Mission"
        assert "Mission" in df.columns
        assert "Name" not in df.columns
        # "Totals" row dropped by int cast
        assert len(df) == 3
        assert df["FY"].dtype == "int64"
        # Budget cleaned
        assert df["Budget"].dtype == "float64"


class TestCSVSourceFiscalYearConversion:
    """FY conversion with CSV files."""

    def test_auto_detect_fiscal_year_column(self, tmp_path):
        """A CSV with 'Fiscal Year' column gets auto-converted to datetime."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Amount\n2020,100\n2021,200\n2022,300\n")

        source = CSVSource(csv_path=str(csv_file))
        df = source.data()

        assert pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"])
        assert df["Fiscal Year"].iloc[0] == datetime(2020, 1, 1)

    def test_auto_detect_year_column(self, tmp_path):
        """A CSV with 'Year' column gets auto-converted to datetime."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Year,Value\n2020,10\n2021,20\n")

        source = CSVSource(csv_path=str(csv_file))
        df = source.data()

        assert pd.api.types.is_datetime64_any_dtype(df["Year"])

    def test_fy_disabled_with_false(self, tmp_path):
        """fiscal_year_column=False prevents conversion."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Amount\n2020,100\n2021,200\n")

        source = CSVSource(csv_path=str(csv_file), fiscal_year_column=False)
        df = source.data()

        assert not pd.api.types.is_datetime64_any_dtype(df["Fiscal Year"])
        assert df["Fiscal Year"].iloc[0] == 2020

    def test_fy_filters_totals_row(self, tmp_path):
        """FY conversion filters out non-numeric rows like 'Totals'."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Year,Amount\n2020,100\n2021,200\nTotals,300\n")

        source = CSVSource(csv_path=str(csv_file))
        df = source.data()

        assert len(df) == 2
        assert pd.api.types.is_datetime64_any_dtype(df["Year"])
