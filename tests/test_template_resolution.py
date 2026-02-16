"""Tests for {{...}} template resolution before Pydantic validation.

Covers the fix where `tpsplots validate` failed on template references
in non-string typed fields (bool, float, int, list) because Pydantic
validation ran before template resolution.
"""

import textwrap
from unittest.mock import patch

import pytest

from tpsplots.exceptions import ConfigurationError
from tpsplots.processors.resolvers.reference_resolver import ReferenceResolver
from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

# ------------------------------------------------------------------
# ReferenceResolver.contains_references
# ------------------------------------------------------------------


class TestContainsReferences:
    """Unit tests for the contains_references fast-path utility."""

    def test_plain_string(self):
        assert ReferenceResolver.contains_references("hello") is False

    def test_template_string(self):
        assert ReferenceResolver.contains_references("{{col}}") is True

    def test_embedded_template(self):
        assert ReferenceResolver.contains_references("FY {{year}} Budget") is True

    def test_nested_dict(self):
        assert ReferenceResolver.contains_references({"a": 1, "b": "{{x}}"}) is True

    def test_nested_list(self):
        assert ReferenceResolver.contains_references([1, "{{y}}", 3]) is True

    def test_deeply_nested(self):
        value = {"level1": {"level2": [{"level3": "{{deep}}"}]}}
        assert ReferenceResolver.contains_references(value) is True

    def test_no_refs_in_dict(self):
        assert ReferenceResolver.contains_references({"a": 1, "b": "hello"}) is False

    def test_no_refs_in_list(self):
        assert ReferenceResolver.contains_references([1, 2, "hello"]) is False

    def test_non_collection(self):
        assert ReferenceResolver.contains_references(42) is False
        assert ReferenceResolver.contains_references(None) is False
        assert ReferenceResolver.contains_references(True) is False


# ------------------------------------------------------------------
# Template resolution before validation (YAMLChartProcessor)
# ------------------------------------------------------------------


class TestResolveBeforeValidation:
    """Integration tests: {{...}} refs in non-string fields pass validation."""

    class DummyView:
        def __init__(self, outdir):
            self.outdir = outdir

        def grouped_bar_plot(self, metadata, stem, **kwargs):
            return {"metadata": metadata, "stem": stem, "kwargs": kwargs}

    def _write_controller(self, tmp_path):
        """Write a minimal controller that returns typed values."""
        ctrl_dir = tmp_path / "tpsplots" / "controllers"
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        (ctrl_dir.parent / "__init__.py").write_text("")
        (ctrl_dir / "__init__.py").write_text("")

        ctrl_path = ctrl_dir / "test_ctrl.py"
        ctrl_path.write_text(
            textwrap.dedent("""\
            from tpsplots.controllers.chart_controller import ChartController

            class TestController(ChartController):
                def typed_fields(self):
                    return {
                        "title": "Test Chart",
                        "groups": [
                            {"label": "G1", "values": [10, 20]},
                            {"label": "G2", "values": [30, 40]},
                        ],
                        "width": 0.35,
                        "show_values": True,
                        "categories": ["A", "B"],
                    }
            """)
        )
        return ctrl_path

    def test_template_refs_in_bool_float_list_fields(self, tmp_path, monkeypatch):
        """{{...}} refs in bool, float, and list fields should validate after resolution."""
        ctrl_path = self._write_controller(tmp_path)

        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent(f"""\
            data:
              source: "controller:{ctrl_path}:typed_fields"

            chart:
              type: grouped_bar
              output: test_chart
              title: "{{{{title}}}}"
              categories: "{{{{categories}}}}"
              groups: "{{{{groups}}}}"
              width: "{{{{width}}}}"
              show_values: "{{{{show_values}}}}"
            """)
        )

        monkeypatch.setattr(
            YAMLChartProcessor, "VIEW_REGISTRY", {"grouped_bar_plot": self.DummyView}
        )

        # This would previously fail with:
        #   chart.grouped_bar.show_values: Input should be a valid boolean
        #   chart.grouped_bar.groups: Input should be a valid list
        #   chart.grouped_bar.width: Input should be a valid number
        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        assert processor.config.chart.show_values is True
        assert processor.config.chart.width == 0.35
        assert len(processor.config.chart.groups) == 2

    def test_generate_works_after_pre_resolution(self, tmp_path, monkeypatch):
        """generate_chart() should work correctly with pre-resolved data."""
        ctrl_path = self._write_controller(tmp_path)

        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent(f"""\
            data:
              source: "controller:{ctrl_path}:typed_fields"

            chart:
              type: grouped_bar
              output: test_chart
              title: "{{{{title}}}}"
              categories: "{{{{categories}}}}"
              groups: "{{{{groups}}}}"
              width: "{{{{width}}}}"
              show_values: "{{{{show_values}}}}"
            """)
        )

        monkeypatch.setattr(
            YAMLChartProcessor, "VIEW_REGISTRY", {"grouped_bar_plot": self.DummyView}
        )

        processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
        result = processor.generate_chart()

        assert result["stem"] == "test_chart"
        assert result["kwargs"]["width"] == 0.35
        assert result["kwargs"]["show_values"] is True


class TestNoRefsFastPath:
    """Configs without {{...}} should not trigger data loading."""

    def test_no_refs_skips_data_loading(self, tmp_path):
        """When no {{...}} refs exist, DataResolver should not be called."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("Year,Value\n2024,10\n")

        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent(f"""\
            data:
              source: csv:{csv_path}

            chart:
              type: line
              output: test_chart
              title: "No Refs Here"
              x: Year
              y: Value
            """)
        )

        with patch.object(ReferenceResolver, "resolve", wraps=ReferenceResolver.resolve) as mock:
            processor = YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
            # resolve should NOT have been called during __init__ (no refs)
            mock.assert_not_called()
            # data should NOT have been loaded
            assert processor.data is None


class TestDataSourceFailure:
    """Error handling when data loading fails during template resolution."""

    def test_missing_controller_raises_clear_error(self, tmp_path):
        """Missing controller should produce a clear error, not a template-ref error."""
        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent("""\
            data:
              source: nonexistent_controller.some_method

            chart:
              type: grouped_bar
              output: test
              title: "{{title}}"
              groups: "{{groups}}"
            """)
        )

        with pytest.raises((ConfigurationError, Exception), match=r"(?i)controller|import|module"):
            YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")

    def test_data_section_validation_error(self, tmp_path):
        """Invalid data section should raise ConfigurationError, not template errors."""
        yaml_path = tmp_path / "chart.yaml"
        yaml_path.write_text(
            textwrap.dedent("""\
            data: {}

            chart:
              type: grouped_bar
              output: test
              title: "{{title}}"
              groups: "{{groups}}"
            """)
        )

        with pytest.raises(ConfigurationError):
            YAMLChartProcessor(yaml_path, outdir=tmp_path / "charts")
