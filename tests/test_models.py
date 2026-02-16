"""Tests for Pydantic models and schema generation (v2.0 spec)."""

import pytest
from pydantic import TypeAdapter, ValidationError


class TestSchema:
    """Tests for JSON Schema generation."""

    def test_get_json_schema(self):
        """Test that JSON schema can be generated."""
        from tpsplots.schema import get_json_schema

        schema = get_json_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "title" in schema

    def test_get_chart_types(self):
        """Test that chart types can be retrieved."""
        from tpsplots.schema import get_chart_types

        types = get_chart_types()
        assert isinstance(types, list)
        # v2.0 uses simplified names
        assert "line" in types
        assert "bar" in types
        assert "scatter" in types

    def test_get_data_source_types(self):
        """Test that data source prefixes can be retrieved."""
        from tpsplots.schema import get_data_source_types

        types = get_data_source_types()
        assert "controller" in types
        assert "csv" in types
        assert "url" in types


class TestModels:
    """Tests for Pydantic models (v2.0 spec).

    ChartConfig is a discriminated union (type alias), not a callable class.
    Use TypeAdapter to construct from dicts, or use specific config classes.
    """

    def test_chart_config_valid(self):
        """Test valid ChartConfig with v2.0 structure."""
        from tpsplots.models import ChartConfig, LineChartConfig

        adapter = TypeAdapter(ChartConfig)
        config = adapter.validate_python(
            {"type": "line", "output": "test_chart", "title": "Test Chart"}
        )
        assert isinstance(config, LineChartConfig)
        assert config.type == "line"
        assert config.output == "test_chart"
        assert config.title == "Test Chart"

    def test_chart_config_invalid_type(self):
        """Test that invalid chart type raises error."""
        from tpsplots.models import ChartConfig

        adapter = TypeAdapter(ChartConfig)
        with pytest.raises(ValidationError):
            adapter.validate_python({"type": "invalid_type", "output": "test", "title": "Test"})

    def test_chart_config_with_all_metadata(self):
        """Test ChartConfig with all metadata fields."""
        from tpsplots.models import BarChartConfig

        config = BarChartConfig(
            type="bar",
            output="test_bar",
            title="Test Title",
            subtitle="Test Subtitle",
            source="Test Source",
        )
        assert config.title == "Test Title"
        assert config.subtitle == "Test Subtitle"
        assert config.source == "Test Source"

    def test_chart_config_scatter_type_valid(self):
        """Test ChartConfig accepts scatter chart type."""
        from tpsplots.models import ChartConfig, ScatterChartConfig

        adapter = TypeAdapter(ChartConfig)
        config = adapter.validate_python(
            {"type": "scatter", "output": "test_scatter", "title": "Test Scatter"}
        )
        assert isinstance(config, ScatterChartConfig)
        assert config.type == "scatter"

    def test_chart_config_extra_params(self):
        """Test that ChartConfig dispatches and accepts typed parameters."""
        from tpsplots.models import LineChartConfig

        config = LineChartConfig(
            type="line",
            output="test",
            title="Test",
            grid=True,
            legend=False,
            color="NeptuneBlue",
        )
        params = config.model_dump(exclude_none=True)
        assert params["grid"] is True
        assert params["legend"] is False
        assert params["color"] == "NeptuneBlue"

    def test_data_source_config(self):
        """Test DataSourceConfig model (v2.0)."""
        from tpsplots.models import DataSourceConfig

        source = DataSourceConfig(source="data.csv")
        assert source.source == "data.csv"

    def test_yaml_chart_config(self):
        """Test complete YAMLChartConfig with v2.0 structure."""
        from tpsplots.models import YAMLChartConfig

        config = YAMLChartConfig(
            data={"source": "test.csv"},
            chart={
                "type": "line",
                "output": "test_chart",
                "title": "Test Chart",
                "x": "{{x_column}}",
                "y": "{{y_column}}",
            },
        )
        assert config.data.source == "test.csv"
        assert config.chart.type == "line"
        assert config.chart.output == "test_chart"
