"""Tests for YAMLChartProcessor.

Tests focus on:
- Bug 5: All color parameters should be resolved from semantic names
- Core chart generation: parameter resolution, metadata flow, view dispatch
"""

import textwrap
from typing import ClassVar

import pytest

from tpsplots.exceptions import ConfigurationError
from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor


class TestColorParameterResolution:
    """Tests for color parameter resolution completeness - Bug 5 fix."""

    # This is the list of color params that SHOULD be resolved
    # If any of these are missing from ColorResolver.COLOR_FIELDS, semantic colors won't work
    EXPECTED_COLOR_PARAMS: ClassVar[list[str]] = [
        # Original 8 params
        "color",
        "colors",
        "positive_color",
        "negative_color",
        "value_color",
        "center_color",
        "end_marker_color",
        "offset_line_color",
        # Missing params (Bug 5)
        "start_marker_color",
        "start_marker_edgecolor",
        "end_marker_edgecolor",
        "line_colors",
        "hline_colors",
        "edgecolor",
        "y_tick_color",
        "pie_edge_color",
    ]

    def test_color_params_list_is_complete(self):
        """Verify all expected color params are in ColorResolver.COLOR_FIELDS."""
        from tpsplots.processors.resolvers import ColorResolver

        # Check that each expected param is in COLOR_FIELDS
        for param in self.EXPECTED_COLOR_PARAMS:
            assert param in ColorResolver.COLOR_FIELDS, (
                f"Color param '{param}' not found in ColorResolver.COLOR_FIELDS. "
                f"Users using semantic color names for {param} will get errors."
            )

    def test_processor_uses_resolve_deep(self):
        """Verify processor uses ColorResolver.resolve_deep() for recursive resolution."""
        import inspect

        # Get the source of the generate_chart method
        source = inspect.getsource(YAMLChartProcessor.generate_chart)

        # Verify it uses resolve_deep (not field-by-field resolution)
        assert "ColorResolver.resolve_deep" in source, (
            "YAMLChartProcessor.generate_chart() should use ColorResolver.resolve_deep() "
            "for recursive color resolution in nested structures like subplot_data."
        )

    def test_color_resolution_handles_lists(self):
        """Color params that accept lists should resolve each item."""
        from tpsplots.processors.resolvers import ColorResolver

        # Test list of semantic colors
        colors = ["Neptune Blue", "Rocket Flame", "Plasma Purple"]
        resolved = ColorResolver.resolve(colors)

        assert resolved == ["#037CC2", "#FF5D47", "#643788"]

    def test_color_resolution_handles_single_values(self):
        """Color params that accept single values should resolve correctly."""
        from tpsplots.processors.resolvers import ColorResolver

        color = "Neptune Blue"
        resolved = ColorResolver.resolve(color)

        assert resolved == "#037CC2"

    def test_color_resolution_passes_through_hex(self):
        """Hex colors should pass through unchanged."""
        from tpsplots.processors.resolvers import ColorResolver

        hex_color = "#FF0000"
        resolved = ColorResolver.resolve(hex_color)

        assert resolved == "#FF0000"

    def test_color_resolution_passes_through_named_colors(self):
        """Standard matplotlib color names should pass through."""
        from tpsplots.processors.resolvers import ColorResolver

        named_color = "red"
        resolved = ColorResolver.resolve(named_color)

        # Non-TPS colors pass through unchanged
        assert resolved == "red"


class TestYAMLChartProcessorCore:
    """Core behavior tests for YAMLChartProcessor."""

    class DummyView:
        """Minimal view used to capture inputs without rendering charts."""

        def __init__(self, outdir):
            self.outdir = outdir
            self.called = None

        def line_plot(self, metadata, stem, **kwargs):
            self.called = {"metadata": metadata, "stem": stem, "kwargs": kwargs}
            return self.called

    class DummyScatterView:
        """Minimal scatter view used to verify scatter dispatch."""

        def __init__(self, outdir):
            self.outdir = outdir
            self.called = None

        def scatter_plot(self, metadata, stem, **kwargs):
            self.called = {"metadata": metadata, "stem": stem, "kwargs": kwargs}
            return self.called

    def test_generate_chart_resolves_params_and_colors(self, tmp_path, monkeypatch):
        """Processor should resolve references and semantic colors before plotting."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n")

        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                data:
                  source: csv:{csv_path}

                chart:
                  type: line
                  output: test_chart
                  title: "Test Chart"
                  subtitle: "Simple subtitle"
                  x: "{{{{Year}}}}"
                  y: "{{{{Value}}}}"
                  color: "Neptune Blue"
                """
            ).strip()
        )

        monkeypatch.setattr(
            YAMLChartProcessor,
            "VIEW_REGISTRY",
            {"line_plot": self.DummyView},
        )

        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        result = processor.generate_chart()

        assert result["stem"] == "test_chart"
        assert result["metadata"]["title"] == "Test Chart"
        assert list(result["kwargs"]["x"]) == [2024, 2025]
        assert list(result["kwargs"]["y"]) == [10, 20]
        assert result["kwargs"]["color"] == "#037CC2"

    def test_unknown_view_type_raises(self, tmp_path, monkeypatch):
        """Unknown view type should raise ConfigurationError."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("Year,Value\n2024,10\n")

        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                data:
                  source: csv:{csv_path}

                chart:
                  type: line
                  output: test_chart
                  title: "Test Chart"
                  x: "{{{{Year}}}}"
                  y: "{{{{Value}}}}"
                """
            ).strip()
        )

        monkeypatch.setattr(YAMLChartProcessor, "VIEW_REGISTRY", {})

        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        with pytest.raises(ConfigurationError, match="Unknown chart type"):
            processor.generate_chart()

    def test_scatter_type_dispatches_to_scatter_plot(self, tmp_path, monkeypatch):
        """Scatter chart type should dispatch to scatter_plot view method."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("Year,Value\n2024,10\n2025,20\n")

        yaml_path = tmp_path / "scatter.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                data:
                  source: csv:{csv_path}

                chart:
                  type: scatter
                  output: scatter_chart
                  title: "Scatter Test"
                  x: "{{{{Year}}}}"
                  y: "{{{{Value}}}}"
                """
            ).strip()
        )

        monkeypatch.setattr(
            YAMLChartProcessor,
            "VIEW_REGISTRY",
            {"scatter_plot": self.DummyScatterView},
        )

        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        result = processor.generate_chart()

        assert result["stem"] == "scatter_chart"
        assert list(result["kwargs"]["x"]) == [2024, 2025]
        assert list(result["kwargs"]["y"]) == [10, 20]

    def test_series_overrides_expand_to_series_n_kwargs(self, tmp_path, monkeypatch):
        """Typed series_overrides should reach line view as series_<n> kwargs."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("Year,A,B\n2024,10,30\n2025,20,40\n")

        yaml_path = tmp_path / "series_overrides.yaml"
        yaml_path.write_text(
            textwrap.dedent(
                f"""
                data:
                  source: csv:{csv_path}

                chart:
                  type: line
                  output: line_series_override
                  title: "Series Override"
                  x: "{{{{Year}}}}"
                  y:
                    - "{{{{A}}}}"
                    - "{{{{B}}}}"
                  series_0:
                    color: "Neptune Blue"
                    linewidth: 5
                """
            ).strip()
        )

        monkeypatch.setattr(
            YAMLChartProcessor,
            "VIEW_REGISTRY",
            {"line_plot": self.DummyView},
        )

        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        result = processor.generate_chart()

        assert "series_overrides" not in result["kwargs"]
        assert "series_0" in result["kwargs"]
        assert result["kwargs"]["series_0"]["linewidth"] == 5
        assert result["kwargs"]["series_0"]["color"] == "#037CC2"
