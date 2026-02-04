"""Tests for DataResolver params and inflation adjustment functionality."""

import pandas as pd
import pytest

from tpsplots.exceptions import DataSourceError
from tpsplots.models.data_sources import DataSourceConfig, DataSourceParams, InflationConfig
from tpsplots.processors.resolvers.data_resolver import DataResolver
from tpsplots.utils.dataframe_transforms import (
    VALID_CAST_TYPES,
    apply_column_cast,
    apply_column_renames,
    filter_columns,
)


class TestDataSourceParams:
    """Tests for DataSourceParams model validation."""

    def test_all_fields_optional(self):
        """Test that all fields have sensible defaults."""
        params = DataSourceParams()
        assert params.columns is None
        assert params.cast is None
        assert params.renames is None
        assert params.auto_clean_currency is None

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


class TestInflationConfig:
    """Tests for InflationConfig model validation."""

    def test_columns_required(self):
        """Test that columns is a required field."""
        with pytest.raises(Exception):  # Pydantic ValidationError
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
        with pytest.raises(Exception):  # Pydantic ValidationError
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
        with pytest.raises(Exception):
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
        )
        result = DataResolver._params_to_kwargs(params)
        assert result == {
            "columns": ["A"],
            "cast": {"A": "int"},
            "renames": {"B": "C"},
            "auto_clean_currency": True,
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


class TestDataFrameTransforms:
    """Tests for dataframe transform utilities."""

    def test_valid_cast_types_constant(self):
        """Test that VALID_CAST_TYPES contains expected types."""
        assert "int" in VALID_CAST_TYPES
        assert "float" in VALID_CAST_TYPES
        assert "str" in VALID_CAST_TYPES
        assert "datetime" in VALID_CAST_TYPES

    def test_apply_column_cast_int(self):
        """Test casting to int."""
        df = pd.DataFrame({"col": ["1", "2", "3"]})
        result = apply_column_cast(df, {"col": "int"})
        assert result["col"].dtype == "Int64"
        assert list(result["col"]) == [1, 2, 3]

    def test_apply_column_cast_float(self):
        """Test casting to float."""
        df = pd.DataFrame({"col": ["1.5", "2.5", "3.5"]})
        result = apply_column_cast(df, {"col": "float"})
        assert result["col"].dtype == "float64"

    def test_apply_column_cast_unknown_type_warns(self, caplog):
        """Test that unknown cast types log a warning."""
        df = pd.DataFrame({"col": ["1", "2"]})
        result = apply_column_cast(df, {"col": "unknown_type"})
        # Column should be unchanged
        assert list(result["col"]) == ["1", "2"]
        assert "Unknown cast type 'unknown_type'" in caplog.text

    def test_apply_column_renames(self):
        """Test column renaming."""
        df = pd.DataFrame({"old": [1, 2]})
        result = apply_column_renames(df, {"old": "new"})
        assert "new" in result.columns
        assert "old" not in result.columns

    def test_filter_columns_success(self):
        """Test filtering to specified columns."""
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        result = filter_columns(df, ["a", "c"])
        assert list(result.columns) == ["a", "c"]

    def test_filter_columns_missing_raises_error(self):
        """Test that missing columns raise DataSourceError."""
        df = pd.DataFrame({"a": [1], "b": [2]})
        with pytest.raises(DataSourceError, match="Columns not found"):
            filter_columns(df, ["a", "missing"])


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
        )
        assert controller.csv_path == "test.csv"
        assert controller.cast == {"col": "int"}
        assert controller.columns == ["col"]
        assert controller.renames == {"old": "new"}
        assert controller.auto_clean_currency is True
