"""Tests for Pydantic models and schema generation (v2.0 spec)."""

import pytest


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
    """Tests for Pydantic models (v2.0 spec)."""

    def test_chart_config_valid(self):
        """Test valid ChartConfig with v2.0 structure."""
        from tpsplots.models import ChartConfig

        # v2.0: type uses simplified name, output instead of output_name, title required
        config = ChartConfig(type="line", output="test_chart", title="Test Chart")
        assert config.type == "line"
        assert config.output == "test_chart"
        assert config.title == "Test Chart"

    def test_chart_config_invalid_type(self):
        """Test that invalid chart type raises error."""
        from pydantic import ValidationError

        from tpsplots.models import ChartConfig

        with pytest.raises(ValidationError):
            ChartConfig(type="invalid_type", output="test", title="Test")

    def test_chart_config_with_all_metadata(self):
        """Test ChartConfig with all metadata fields."""
        from tpsplots.models import ChartConfig

        config = ChartConfig(
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
        from tpsplots.models import ChartConfig

        config = ChartConfig(type="scatter", output="test_scatter", title="Test Scatter")
        assert config.type == "scatter"

    def test_chart_config_extra_params(self):
        """Test that ChartConfig accepts extra parameters."""
        from tpsplots.models import ChartConfig

        config = ChartConfig(
            type="line",
            output="test",
            title="Test",
            grid=True,
            legend=False,
            color="NeptuneBlue",
        )
        # Extra params should be accessible via model_dump
        params = config.model_dump()
        assert params["grid"] is True
        assert params["legend"] is False
        assert params["color"] == "NeptuneBlue"

    def test_metadata_config(self):
        """Test legacy MetadataConfig model."""
        from tpsplots.models import MetadataConfig

        metadata = MetadataConfig(
            title="Test Title",
            subtitle="Test Subtitle",
            source="Test Source",
        )
        assert metadata.title == "Test Title"

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
