"""Tests for Pydantic models and schema generation."""

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
        assert "line_plot" in types
        assert "bar_plot" in types

    def test_get_data_source_types(self):
        """Test that data source types can be retrieved."""
        from tpsplots.schema import get_data_source_types

        types = get_data_source_types()
        assert "csv_file" in types
        assert "google_sheets" in types
        assert "controller_method" in types


class TestModels:
    """Tests for Pydantic models."""

    def test_chart_config_valid(self):
        """Test valid ChartConfig."""
        from tpsplots.models import ChartConfig

        config = ChartConfig(type="line_plot", output_name="test_chart")
        assert config.type == "line_plot"
        assert config.output_name == "test_chart"

    def test_chart_config_invalid_type(self):
        """Test that invalid chart type raises error."""
        from pydantic import ValidationError

        from tpsplots.models import ChartConfig

        with pytest.raises(ValidationError):
            ChartConfig(type="invalid_type", output_name="test")

    def test_metadata_config(self):
        """Test MetadataConfig model."""
        from tpsplots.models import MetadataConfig

        metadata = MetadataConfig(
            title="Test Title",
            subtitle="Test Subtitle",
            source="Test Source",
        )
        assert metadata.title == "Test Title"

    def test_csv_data_source(self):
        """Test CSVFileDataSource model."""
        from tpsplots.models import CSVFileDataSource

        source = CSVFileDataSource(type="csv_file", path="data.csv")
        assert source.type == "csv_file"
        assert source.path == "data.csv"

    def test_url_data_source(self):
        """Test URLDataSource model."""
        from tpsplots.models import URLDataSource

        source = URLDataSource(
            type="google_sheets",
            url="https://docs.google.com/spreadsheets/d/test/export?format=csv",
        )
        assert source.type == "google_sheets"
