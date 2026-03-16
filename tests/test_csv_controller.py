"""Tests for CSVController."""

import pandas as pd

from tpsplots.controllers.csv_controller import CSVController


class TestCSVControllerResultStructure:
    def test_result_has_expected_keys(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Year,Budget\n2020,100.0\n2021,200.0\n")

        result = CSVController(csv_path=str(csv_file), fiscal_year_column=False).load_data()

        assert "data" in result
        assert isinstance(result["data"], pd.DataFrame)
        assert "metadata" in result
        assert "Budget" in result  # column exposed as top-level key


class TestCSVControllerMetadataSums:
    def test_numeric_columns_summed(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Year,Budget,Amount\n2020,100.0,10.0\n2021,200.0,20.0\n")

        result = CSVController(csv_path=str(csv_file), fiscal_year_column=False).load_data()
        sums = result["metadata"]["column_sums"]

        assert sums["Budget"] == 300.0
        assert sums["Amount"] == 30.0

    def test_string_columns_excluded_from_sums(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Label,Value\nfoo,1.0\nbar,2.0\n")

        result = CSVController(csv_path=str(csv_file), fiscal_year_column=False).load_data()
        sums = result["metadata"]["column_sums"]

        assert "Label" not in sums
        assert sums["Value"] == 3.0

    def test_fiscal_year_column_excluded_from_sums(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Budget\n2020,100.0\n2021,200.0\n")

        result = CSVController(csv_path=str(csv_file)).load_data()
        sums = result["metadata"]["column_sums"]

        assert "Fiscal Year" not in sums
        assert sums["Budget"] == 300.0

    def test_raw_columns_excluded_from_sums(self, tmp_path):
        """Currency-cleaned columns preserve originals as _raw; those should be excluded.

        Currency detection requires min_samples=3, so at least 3 rows are needed.
        """
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Label,Cost\nA,$100\nB,$200\nC,$300\n")

        result = CSVController(
            csv_path=str(csv_file),
            fiscal_year_column=False,
            auto_clean_currency=True,
        ).load_data()
        sums = result["metadata"]["column_sums"]

        assert "Cost_raw" not in sums
        assert "Cost" in sums  # cleaned numeric column IS summed
