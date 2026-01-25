"""Tests for CSV export functionality in ChartView.

Tests the _export_csv method which handles:
- Numeric formatting (integers, floats, NaN)
- Date formatting (YYYY-MM-DD)
- Metadata header rows (author, license, source, notes)
"""

from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from tpsplots.views import BarChartView


@pytest.fixture
def view(tmp_path):
    """Provide a BarChartView instance with tmp_path as output directory."""
    return BarChartView(outdir=tmp_path)


@pytest.fixture
def basic_metadata():
    """Minimal metadata for most tests."""
    return {"source": "Test Data Source"}


class TestCSVNumericFormatting:
    """Tests for numeric value formatting in CSV export."""

    def test_integers_export_as_integers(self, view, tmp_path, basic_metadata):
        """Values like 5.0 should export as 5, not 5.0."""
        df = pd.DataFrame({"value": [5.0, 100.0, -10.0]})

        view._export_csv(df, basic_metadata, "test_integers")

        csv_path = tmp_path / "test_integers.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows (after blank separator row)
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":  # Blank separator row
                data_start = i + 2  # Skip header row after separator
                break

        assert data_start is not None, "Could not find data section"
        data_lines = lines[data_start:]

        # Verify integers don't have decimal points
        assert data_lines[0] == "5"
        assert data_lines[1] == "100"
        assert data_lines[2] == "-10"

    def test_floats_greater_than_one_round_to_2_decimal_places(
        self, view, tmp_path, basic_metadata
    ):
        """Floats > 1 like 1234.5678 should round to 1234.57."""
        df = pd.DataFrame({"value": [1234.5678, 99.999, -50.125]})

        view._export_csv(df, basic_metadata, "test_float_rounding")

        csv_path = tmp_path / "test_float_rounding.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                data_start = i + 2
                break

        data_lines = lines[data_start:]

        assert data_lines[0] == "1234.57"
        # Note: 99.999 rounds to 100.0 but integer check happens before rounding
        assert data_lines[1] == "100.0"
        assert data_lines[2] == "-50.12"

    def test_floats_less_than_or_equal_to_one_export_raw(self, view, tmp_path, basic_metadata):
        """Floats ≤ 1 like 0.123456 should stay as raw values."""
        df = pd.DataFrame({"value": [0.123456, 0.9999, 1.0, -0.5]})

        view._export_csv(df, basic_metadata, "test_small_floats")

        csv_path = tmp_path / "test_small_floats.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                data_start = i + 2
                break

        data_lines = lines[data_start:]

        # Small floats (abs <= 1) preserve full precision
        assert data_lines[0] == "0.123456"
        assert data_lines[1] == "0.9999"
        assert data_lines[2] == "1"  # 1.0 is an integer
        assert data_lines[3] == "-0.5"

    def test_nan_exports_as_empty_string(self, view, tmp_path, basic_metadata):
        """NaN values should export as empty strings."""
        df = pd.DataFrame({"value": [1.0, np.nan, 3.0, float("nan")]})

        view._export_csv(df, basic_metadata, "test_nan")

        csv_path = tmp_path / "test_nan.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                data_start = i + 2
                break

        data_lines = lines[data_start:]

        assert data_lines[0] == "1"
        assert data_lines[1] == '""'  # NaN becomes empty (csv.writer quotes it)
        assert data_lines[2] == "3"
        assert data_lines[3] == '""'  # float('nan') also becomes empty


class TestCSVDateFormatting:
    """Tests for date formatting in CSV export."""

    def test_dates_format_as_yyyy_mm_dd(self, view, tmp_path, basic_metadata):
        """Datetime objects should format as YYYY-MM-DD without time component."""
        df = pd.DataFrame(
            {
                "event_date": [
                    datetime(2024, 1, 15, 10, 30, 45),
                    date(2023, 12, 31),
                    pd.Timestamp("2022-06-15 08:00:00"),
                ]
            }
        )

        view._export_csv(df, basic_metadata, "test_dates")

        csv_path = tmp_path / "test_dates.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                data_start = i + 2
                break

        data_lines = lines[data_start:]

        assert data_lines[0] == "2024-01-15"
        assert data_lines[1] == "2023-12-31"
        assert data_lines[2] == "2022-06-15"


class TestCSVMetadata:
    """Tests for metadata rows in CSV export."""

    def test_author_row_present(self, view, tmp_path):
        """CSV should contain author attribution row."""
        df = pd.DataFrame({"x": [1]})
        metadata = {}

        view._export_csv(df, metadata, "test_author")

        csv_path = tmp_path / "test_author.csv"
        content = csv_path.read_text()

        assert "Casey Dreier/The Planetary Society" in content
        assert "Author," in content

    def test_license_row_present(self, view, tmp_path):
        """CSV should contain CC BY 4.0 license row."""
        df = pd.DataFrame({"x": [1]})
        metadata = {}

        view._export_csv(df, metadata, "test_license")

        csv_path = tmp_path / "test_license.csv"
        content = csv_path.read_text()

        assert "CC BY 4.0" in content
        assert "License," in content

    def test_data_source_from_metadata(self, view, tmp_path):
        """Data source from metadata dict should appear in CSV."""
        df = pd.DataFrame({"x": [1]})
        metadata = {"source": "NASA Budget Data FY2024"}

        view._export_csv(df, metadata, "test_source")

        csv_path = tmp_path / "test_source.csv"
        content = csv_path.read_text()

        assert "NASA Budget Data FY2024" in content
        assert "Data Source," in content

    def test_notes_from_dataframe_attrs(self, view, tmp_path):
        """Notes from df.attrs['export_note'] should appear in CSV."""
        df = pd.DataFrame({"x": [1]})
        df.attrs["export_note"] = "Adjusted for inflation to FY2024 dollars"
        metadata = {}

        view._export_csv(df, metadata, "test_notes")

        csv_path = tmp_path / "test_notes.csv"
        content = csv_path.read_text()

        assert "Adjusted for inflation to FY2024 dollars" in content
        assert "Note," in content

    def test_multiple_notes_from_list(self, view, tmp_path):
        """Multiple notes from list should each appear as separate rows."""
        df = pd.DataFrame({"x": [1]})
        df.attrs["export_note"] = [
            "First note about methodology",
            "Second note about data sources",
        ]
        metadata = {}

        view._export_csv(df, metadata, "test_multi_notes")

        csv_path = tmp_path / "test_multi_notes.csv"
        content = csv_path.read_text()

        assert "First note about methodology" in content
        assert "Second note about data sources" in content
        # Both should be prefixed with "Note,"
        assert content.count("Note,") == 2

    def test_blank_separator_row_before_data(self, view, tmp_path):
        """A blank row should separate metadata from data."""
        df = pd.DataFrame({"x": [1]})
        metadata = {"source": "Test"}

        view._export_csv(df, metadata, "test_separator")

        csv_path = tmp_path / "test_separator.csv"
        content = csv_path.read_text()
        lines = content.split("\n")

        # Find blank separator row (contains only comma)
        separator_found = False
        for i, line in enumerate(lines):
            if line.strip() == ",":
                separator_found = True
                # Next line should be column header
                assert lines[i + 1].strip() == "x"
                break

        assert separator_found, "Blank separator row not found"


class TestCSVBasicFunctionality:
    """Tests for basic CSV export functionality."""

    def test_csv_file_created_at_correct_path(self, view, tmp_path, basic_metadata):
        """CSV file should be created at outdir/stem.csv."""
        df = pd.DataFrame({"x": [1, 2, 3]})

        result_path = view._export_csv(df, basic_metadata, "my_chart")

        expected_path = tmp_path / "my_chart.csv"
        assert expected_path.exists()
        assert result_path == expected_path

    def test_column_headers_written_correctly(self, view, tmp_path, basic_metadata):
        """Column names should appear after metadata section."""
        df = pd.DataFrame({"year": [2020, 2021], "budget": [100, 200]})

        view._export_csv(df, basic_metadata, "test_headers")

        csv_path = tmp_path / "test_headers.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find header row (first non-metadata row after blank separator)
        header_idx = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                header_idx = i + 1
                break

        assert header_idx is not None
        assert lines[header_idx] == "year,budget"

    def test_multiple_rows_written_correctly(self, view, tmp_path, basic_metadata):
        """Multiple data rows should be written in order."""
        df = pd.DataFrame({"category": ["A", "B", "C"], "value": [10.0, 20.0, 30.0]})

        view._export_csv(df, basic_metadata, "test_rows")

        csv_path = tmp_path / "test_rows.csv"
        content = csv_path.read_text()
        lines = content.strip().split("\n")

        # Find data rows
        data_start = None
        for i, line in enumerate(lines):
            if line.strip() == ",":
                data_start = i + 2  # Skip header
                break

        data_lines = lines[data_start:]

        assert data_lines[0] == "A,10"
        assert data_lines[1] == "B,20"
        assert data_lines[2] == "C,30"

    def test_string_values_preserved(self, view, tmp_path, basic_metadata):
        """String values should be preserved as-is."""
        df = pd.DataFrame({"name": ["Mercury", "Venus", "Earth"]})

        view._export_csv(df, basic_metadata, "test_strings")

        csv_path = tmp_path / "test_strings.csv"
        content = csv_path.read_text()

        assert "Mercury" in content
        assert "Venus" in content
        assert "Earth" in content
