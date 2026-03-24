"""Tests for CSVController."""

import pandas as pd

from tpsplots.controllers.csv_controller import CSVController
from tpsplots.models.data_sources import DataSourceConfig, DataSourceParams
from tpsplots.processors.resolvers.data_resolver import DataResolver


def _resolve_csv(path, **params_kwargs) -> dict:
    """Helper: resolve a CSV file through DataResolver (column sums included)."""
    params = DataSourceParams(**params_kwargs) if params_kwargs else None
    config = DataSourceConfig(source=str(path), params=params)
    return DataResolver.resolve(config)


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
    """Column sums are computed by DataResolver after all transformations."""

    def test_numeric_columns_summed(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Year,Budget,Amount\n2020,100.0,10.0\n2021,200.0,20.0\n")

        result = _resolve_csv(csv_file, fiscal_year_column=False)
        sums = result["metadata"]["column_sums"]

        assert sums["Budget"] == 300.0
        assert sums["Amount"] == 30.0

    def test_string_columns_excluded_from_sums(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Label,Value\nfoo,1.0\nbar,2.0\n")

        result = _resolve_csv(csv_file, fiscal_year_column=False)
        sums = result["metadata"]["column_sums"]

        assert "Label" not in sums
        assert sums["Value"] == 3.0

    def test_fiscal_year_column_excluded_from_sums(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Budget\n2020,100.0\n2021,200.0\n")

        result = _resolve_csv(csv_file)
        sums = result["metadata"]["column_sums"]

        assert "Fiscal Year" not in sums
        assert sums["Budget"] == 300.0

    def test_raw_columns_excluded_from_sums(self, tmp_path):
        """Currency-cleaned columns preserve originals as _raw; those should be excluded.

        Currency detection requires min_samples=3, so at least 3 rows are needed.
        """
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Label,Cost\nA,$100\nB,$200\nC,$300\n")

        result = _resolve_csv(csv_file, fiscal_year_column=False, auto_clean_currency=True)
        sums = result["metadata"]["column_sums"]

        assert "Cost_raw" not in sums
        assert "Cost" in sums  # cleaned numeric column IS summed


class TestCSVControllerValueMetadata:
    def test_numeric_columns_expose_min_max_metadata(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text(
            "Fiscal Year,Budget Amount,Headcount,Label\n"
            "2020,100.0,10,Alpha\n"
            "2021,250.0,12,Beta\n"
            "2022,175.0,9,Gamma\n"
        )

        result = CSVController(csv_path=str(csv_file)).load_data()
        metadata = result["metadata"]

        assert metadata["max_budget_amount"] == 250.0
        assert metadata["min_budget_amount"] == 100.0
        assert metadata["max_budget_amount_fiscal_year"] == 2022
        assert metadata["min_budget_amount_fiscal_year"] == 2020
        assert metadata["max_headcount"] == 12.0
        assert metadata["min_headcount"] == 9.0
        assert "max_label" not in metadata
