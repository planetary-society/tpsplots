"""Tests for the shared render pipeline.

Tests ``build_render_context()`` and ``expand_series_overrides()`` directly,
verifying the canonical pipeline shared by CLI and editor preview paths.
"""

import textwrap

from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.render_pipeline import (
    RenderContext,
    build_render_context,
    expand_series_overrides,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config_and_data(tmp_path, yaml_text):
    """Write CSV + YAML and return (validated_config, resolved_data)."""
    from tpsplots.processors.resolvers import DataResolver

    yaml_path = tmp_path / "chart.yaml"
    yaml_path.write_text(textwrap.dedent(yaml_text).strip())

    import yaml

    raw = yaml.safe_load(yaml_path.read_text())
    validated = YAMLChartConfig(**raw)
    data = DataResolver.resolve(validated.data)
    return validated, data


# ---------------------------------------------------------------------------
# build_render_context basics
# ---------------------------------------------------------------------------


class TestBuildRenderContext:
    def test_returns_render_context(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("Year,Value\n2024,10\n2025,20\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: line
              output: test_output
              title: "My Title"
              subtitle: "My Subtitle"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
            """,
        )

        ctx = build_render_context(validated, data)

        assert isinstance(ctx, RenderContext)
        assert ctx.chart_type_v1 == "line_plot"
        assert ctx.output_name == "test_output"
        assert ctx.resolved_metadata == {"title": "My Title", "subtitle": "My Subtitle"}
        assert list(ctx.resolved_params["x"]) == [2024, 2025]
        assert list(ctx.resolved_params["y"]) == [10, 20]

    def test_resolves_semantic_colors(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("Year,Value\n2024,10\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: line
              output: color_test
              title: "Color Test"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
              color: "Neptune Blue"
            """,
        )

        ctx = build_render_context(validated, data)
        assert ctx.resolved_params["color"] == "#037CC2"

    def test_metadata_fields_not_in_params(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("Category,Amount\nA,100\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: bar
              output: meta_test
              title: "Title"
              subtitle: "Sub"
              source: "Source Text"
              categories: "{{{{Category}}}}"
              values: "{{{{Amount}}}}"
            """,
        )

        ctx = build_render_context(validated, data)
        assert "title" not in ctx.resolved_params
        assert "subtitle" not in ctx.resolved_params
        assert "source" not in ctx.resolved_params
        assert ctx.resolved_metadata["title"] == "Title"
        assert ctx.resolved_metadata["subtitle"] == "Sub"
        assert ctx.resolved_metadata["source"] == "Source Text"

    def test_control_fields_not_in_params(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text("Category,Amount\nA,100\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: bar
              output: ctrl_test
              title: "Title"
              categories: "{{{{Category}}}}"
              values: "{{{{Amount}}}}"
            """,
        )

        ctx = build_render_context(validated, data)
        assert "type" not in ctx.resolved_params
        assert "output" not in ctx.resolved_params


# ---------------------------------------------------------------------------
# Escape hatch (matplotlib_config) conflict detection
# ---------------------------------------------------------------------------


class TestEscapeHatchConflicts:
    def test_log_conflicts_true_warns(self, tmp_path, caplog):
        """With log_conflicts=True, overlapping keys should produce a warning."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,Value\n2024,10\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: line
              output: escape_test
              title: "Test"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
              linewidth: 3
              matplotlib_config:
                linewidth: 5
            """,
        )

        with caplog.at_level("WARNING"):
            ctx = build_render_context(validated, data, log_conflicts=True)

        assert ctx.resolved_params["linewidth"] == 5  # escape hatch wins
        assert "overlap" in caplog.text.lower() or "override" in caplog.text.lower()

    def test_log_conflicts_false_silent(self, tmp_path, caplog):
        """With log_conflicts=False, overlapping keys should be silent."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,Value\n2024,10\n")

        validated, data = _make_config_and_data(
            tmp_path,
            f"""
            data:
              source: csv:{csv}

            chart:
              type: line
              output: escape_test_silent
              title: "Test"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
              linewidth: 3
              matplotlib_config:
                linewidth: 5
            """,
        )

        with caplog.at_level("WARNING"):
            ctx = build_render_context(validated, data, log_conflicts=False)

        assert ctx.resolved_params["linewidth"] == 5
        conflict_warnings = [
            r
            for r in caplog.records
            if "overlap" in r.message.lower() or "override" in r.message.lower()
        ]
        assert len(conflict_warnings) == 0


# ---------------------------------------------------------------------------
# expand_series_overrides
# ---------------------------------------------------------------------------


class TestExpandSeriesOverrides:
    def test_numeric_keys_expand(self):
        params = {"x": [1, 2], "series_overrides": {0: {"color": "red"}, 1: {"color": "blue"}}}
        result = expand_series_overrides(params)
        assert result["series_0"] == {"color": "red"}
        assert result["series_1"] == {"color": "blue"}
        assert "series_overrides" not in result

    def test_string_numeric_keys_expand(self):
        params = {"x": [1, 2], "series_overrides": {"0": {"lw": 2}, "1": {"lw": 3}}}
        result = expand_series_overrides(params)
        assert result["series_0"] == {"lw": 2}
        assert result["series_1"] == {"lw": 3}

    def test_non_numeric_key_skipped(self, caplog):
        params = {"series_overrides": {"main": {"color": "red"}}}
        with caplog.at_level("WARNING"):
            result = expand_series_overrides(params)
        assert "series_main" not in result
        assert "non-numeric" in caplog.text.lower()

    def test_no_overrides_passthrough(self):
        params = {"x": [1, 2], "y": [3, 4]}
        result = expand_series_overrides(params)
        assert result == {"x": [1, 2], "y": [3, 4]}

    def test_empty_overrides_passthrough(self):
        params = {"x": [1], "series_overrides": {}}
        result = expand_series_overrides(params)
        assert "series_overrides" not in result

    def test_non_dict_overrides_skipped(self, caplog):
        params = {"series_overrides": "not a dict"}
        with caplog.at_level("WARNING"):
            result = expand_series_overrides(params)
        # series_overrides is popped then skipped — key is removed
        assert "series_overrides" not in result
        assert "Expected series_overrides to be a dict" in caplog.text
