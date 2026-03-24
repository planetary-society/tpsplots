"""Tests for DataResolver params and inflation adjustment functionality."""

import pandas as pd
import pytest
from pydantic import ValidationError

from tpsplots.exceptions import DataSourceError
from tpsplots.models.data_sources import DataSourceConfig, DataSourceParams, InflationConfig
from tpsplots.processors.resolvers.data_resolver import DataResolver


class TestDataSourceParams:
    """Tests for DataSourceParams model validation."""

    def test_all_fields_optional(self):
        """Test that all fields have sensible defaults."""
        params = DataSourceParams()
        assert params.columns is None
        assert params.cast is None
        assert params.renames is None
        assert params.auto_clean_currency is None
        assert params.fiscal_year_column is None
        assert params.truncate_at is None

    def test_columns_accepts_list(self):
        """Test columns field accepts list of strings."""
        params = DataSourceParams(columns=["Fiscal Year", "Amount"])
        assert params.columns == ["Fiscal Year", "Amount"]

    def test_cast_accepts_dict(self):
        """Test cast field accepts dict of column to type mappings."""
        params = DataSourceParams(cast={"Year": "int", "Amount": "float"})
        assert params.cast == {"Year": "int", "Amount": "float"}

    def test_renames_accepts_dict(self):
        """Test renames field accepts dict of old to new name mappings."""
        params = DataSourceParams(renames={"Old Name": "New Name"})
        assert params.renames == {"Old Name": "New Name"}

    def test_truncate_at_accepts_false(self):
        """truncate_at accepts False to disable truncation."""
        params = DataSourceParams(truncate_at=False)
        assert params.truncate_at is False

    def test_truncate_at_accepts_string(self):
        """truncate_at accepts a custom exact-match marker."""
        params = DataSourceParams(truncate_at="Totals")
        assert params.truncate_at == "Totals"

    def test_truncate_at_rejects_whitespace_only_string(self):
        """Whitespace-only truncate_at values should be rejected."""
        with pytest.raises(ValidationError):
            DataSourceParams(truncate_at="   ")


class TestInflationConfig:
    """Tests for InflationConfig model validation."""

    def test_columns_required(self):
        """Test that columns is a required field."""
        with pytest.raises(ValidationError):
            InflationConfig()

    def test_type_defaults_to_nnsi(self):
        """Test that type defaults to 'nnsi'."""
        config = InflationConfig(columns=["Amount"])
        assert config.type == "nnsi"

    def test_type_accepts_gdp(self):
        """Test that type accepts 'gdp'."""
        config = InflationConfig(columns=["Amount"], type="gdp")
        assert config.type == "gdp"

    def test_type_rejects_invalid(self):
        """Test that invalid type values are rejected."""
        with pytest.raises(ValidationError):
            InflationConfig(columns=["Amount"], type="invalid")

    def test_fiscal_year_column_default(self):
        """Test fiscal_year_column defaults to 'Fiscal Year'."""
        config = InflationConfig(columns=["Amount"])
        assert config.fiscal_year_column == "Fiscal Year"

    def test_target_year_defaults_to_none(self):
        """Test target_year defaults to None (auto-calculate)."""
        config = InflationConfig(columns=["Amount"])
        assert config.target_year is None


class TestDataSourceConfig:
    """Tests for DataSourceConfig model with params and inflation."""

    def test_source_required(self):
        """Test that source is required."""
        with pytest.raises(ValidationError):
            DataSourceConfig()

    def test_params_optional(self):
        """Test that params is optional."""
        config = DataSourceConfig(source="data.csv")
        assert config.params is None

    def test_calculate_inflation_optional(self):
        """Test that calculate_inflation is optional."""
        config = DataSourceConfig(source="data.csv")
        assert config.calculate_inflation is None

    def test_full_config(self):
        """Test creating a full config with all options."""
        config = DataSourceConfig(
            source="https://example.com/data.csv",
            params=DataSourceParams(
                columns=["Year", "Amount"],
                cast={"Year": "int"},
            ),
            calculate_inflation=InflationConfig(
                columns=["Amount"],
                type="nnsi",
            ),
        )
        assert config.source == "https://example.com/data.csv"
        assert config.params.columns == ["Year", "Amount"]
        assert config.calculate_inflation.type == "nnsi"


class TestParamsToKwargs:
    """Tests for DataResolver._params_to_kwargs helper."""

    def test_none_params_returns_empty_dict(self):
        """Test that None params returns empty dict."""
        result = DataResolver._params_to_kwargs(None)
        assert result == {}

    def test_empty_params_returns_empty_dict(self):
        """Test that params with all None values returns empty dict."""
        params = DataSourceParams()
        result = DataResolver._params_to_kwargs(params)
        assert result == {}

    def test_extracts_non_none_values(self):
        """Test that only non-None values are extracted."""
        params = DataSourceParams(
            columns=["A", "B"],
            cast={"A": "int"},
        )
        result = DataResolver._params_to_kwargs(params)
        assert result == {"columns": ["A", "B"], "cast": {"A": "int"}}
        assert "renames" not in result
        assert "auto_clean_currency" not in result

    def test_all_fields_extracted(self):
        """Test that all non-None fields are extracted."""
        params = DataSourceParams(
            columns=["A"],
            cast={"A": "int"},
            renames={"B": "C"},
            auto_clean_currency=True,
            truncate_at="Totals",
        )
        result = DataResolver._params_to_kwargs(params)
        assert result == {
            "columns": ["A"],
            "cast": {"A": "int"},
            "renames": {"B": "C"},
            "auto_clean_currency": True,
            "truncate_at": "Totals",
        }


class TestApplyInflationAdjustment:
    """Tests for DataResolver._apply_inflation_adjustment."""

    def test_missing_data_key_raises_error(self):
        """Test that missing 'data' key raises DataSourceError."""
        result = {"other": "value"}
        config = InflationConfig(columns=["Amount"])
        with pytest.raises(DataSourceError, match="must contain 'data' DataFrame"):
            DataResolver._apply_inflation_adjustment(result, config)

    def test_non_dataframe_data_raises_error(self):
        """Test that non-DataFrame 'data' raises DataSourceError."""
        result = {"data": "not a dataframe"}
        config = InflationConfig(columns=["Amount"])
        with pytest.raises(DataSourceError, match="must contain 'data' DataFrame"):
            DataResolver._apply_inflation_adjustment(result, config)

    def test_exposes_inflation_target_year(self, mock_nnsi):
        """Test that inflation_target_year is exposed in result."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021, 2022],
                "Amount": [100.0, 200.0, 300.0],
            }
        )
        result = {"data": df}
        config = InflationConfig(columns=["Amount"], target_year=2024)

        updated = DataResolver._apply_inflation_adjustment(result, config)

        assert "inflation_target_year" in updated
        assert updated["inflation_target_year"] == 2024

    def test_creates_adjusted_column(self, mock_nnsi):
        """Test that adjusted columns are created."""
        df = pd.DataFrame(
            {
                "Fiscal Year": [2020, 2021],
                "Amount": [100.0, 200.0],
            }
        )
        result = {"data": df}
        config = InflationConfig(columns=["Amount"], target_year=2024)

        updated = DataResolver._apply_inflation_adjustment(result, config)

        assert "Amount_adjusted_nnsi" in updated
        assert "Amount_adjusted_nnsi" in updated["data"].columns


class TestCSVInflationMetadataAndSums:
    """Column sums and metadata are computed after inflation."""

    def test_inflation_adjusted_columns_in_sums(self, tmp_path, mock_nnsi):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Amount\n2020,100.0\n2021,200.0\n")

        config = DataSourceConfig(
            source=str(csv_file),
            calculate_inflation=InflationConfig(columns=["Amount"], target_year=2024),
        )
        result = DataResolver.resolve(config)
        sums = result["metadata"]["column_sums"]

        assert "Amount" in sums
        assert "Amount_adjusted_nnsi" in sums
        assert sums["Amount_adjusted_nnsi"] > 0

    def test_fiscal_year_excluded_from_sums_with_inflation(self, tmp_path, mock_nnsi):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Budget\n2020,100.0\n2021,200.0\n")

        config = DataSourceConfig(
            source=str(csv_file),
            calculate_inflation=InflationConfig(columns=["Budget"], target_year=2024),
        )
        result = DataResolver.resolve(config)
        sums = result["metadata"]["column_sums"]

        assert "Fiscal Year" not in sums
        assert "Budget" in sums
        assert "Budget_adjusted_nnsi" in sums

    def test_inflation_adjusted_year_in_metadata(self, tmp_path, mock_nnsi):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("Fiscal Year,Amount\n2020,100.0\n2021,200.0\n")

        config = DataSourceConfig(
            source=str(csv_file),
            calculate_inflation=InflationConfig(columns=["Amount"], target_year=2024),
        )
        result = DataResolver.resolve(config)

        assert result["metadata"]["inflation_adjusted_year"] == 2024
        assert result["inflation_target_year"] == 2024


class TestCSVControllerWithParams:
    """Tests for CSVController with the new params."""

    def test_auto_clean_currency_default_true(self):
        """Test that auto_clean_currency defaults to True."""
        from tpsplots.controllers.csv_controller import CSVController

        controller = CSVController(csv_path="test.csv")
        assert controller.auto_clean_currency is True

    def test_auto_clean_currency_explicit_false(self):
        """Test that auto_clean_currency can be set to False."""
        from tpsplots.controllers.csv_controller import CSVController

        controller = CSVController(csv_path="test.csv", auto_clean_currency=False)
        assert controller.auto_clean_currency is False

    def test_all_params_accepted(self):
        """Test that all params are accepted in constructor."""
        from tpsplots.controllers.csv_controller import CSVController

        controller = CSVController(
            csv_path="test.csv",
            cast={"col": "int"},
            columns=["col"],
            renames={"old": "new"},
            auto_clean_currency=True,
            fiscal_year_column="Fiscal Year",
            truncate_at="Totals",
        )
        assert controller.csv_path == "test.csv"
        assert controller.cast == {"col": "int"}
        assert controller.columns == ["col"]
        assert controller.renames == {"old": "new"}
        assert controller.auto_clean_currency is True
        assert controller.fiscal_year_column == "Fiscal Year"
        assert controller.truncate_at == "Totals"

    def test_fiscal_year_column_default_none(self):
        """Test that fiscal_year_column defaults to None."""
        from tpsplots.controllers.csv_controller import CSVController

        controller = CSVController(csv_path="test.csv")
        assert controller.fiscal_year_column is None

    def test_fiscal_year_column_false_disables(self):
        """Test that fiscal_year_column=False disables FY conversion."""
        from tpsplots.controllers.csv_controller import CSVController

        controller = CSVController(csv_path="test.csv", fiscal_year_column=False)
        assert controller.fiscal_year_column is False


class TestParamsToKwargsWithFiscalYear:
    """Tests for _params_to_kwargs with fiscal_year_column."""

    def test_fiscal_year_column_included_when_set(self):
        """fiscal_year_column is included in kwargs when not None."""
        params = DataSourceParams(fiscal_year_column="Year")
        result = DataResolver._params_to_kwargs(params)
        assert result["fiscal_year_column"] == "Year"

    def test_fiscal_year_column_false_included(self):
        """fiscal_year_column=False is included (it's not None)."""
        params = DataSourceParams(fiscal_year_column=False)
        result = DataResolver._params_to_kwargs(params)
        assert result["fiscal_year_column"] is False

    def test_fiscal_year_column_omitted_when_none(self):
        """fiscal_year_column is omitted from kwargs when None."""
        params = DataSourceParams()
        result = DataResolver._params_to_kwargs(params)
        assert "fiscal_year_column" not in result

    def test_params_to_kwargs_csv_controller_accepts_fiscal_year(self):
        """_params_to_kwargs with fiscal_year_column set produces kwargs
        that CSVController accepts without TypeError."""
        from tpsplots.controllers.csv_controller import CSVController

        params = DataSourceParams(
            columns=["Year", "Amount"],
            fiscal_year_column="Year",
        )
        kwargs = {"csv_path": "test.csv", **DataResolver._params_to_kwargs(params)}
        # Should not raise TypeError for unexpected keyword argument
        controller = CSVController(**kwargs)
        assert controller.fiscal_year_column == "Year"

    def test_truncate_at_false_included(self):
        """truncate_at=False is included in kwargs."""
        params = DataSourceParams(truncate_at=False)
        result = DataResolver._params_to_kwargs(params)
        assert result["truncate_at"] is False

    def test_truncate_at_string_included(self):
        """truncate_at custom string is included in kwargs."""
        params = DataSourceParams(truncate_at="Totals")
        result = DataResolver._params_to_kwargs(params)
        assert result["truncate_at"] == "Totals"
