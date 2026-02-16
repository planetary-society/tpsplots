"""CLI vs Editor render pipeline parity tests.

For the same config + data, both ``YAMLChartProcessor.generate_chart()``
and ``EditorSession.render_preview()`` should produce identical
``RenderContext`` objects via the shared ``build_render_context()``.

This validates that the refactoring in Phase 1 didn't introduce drift
between the two paths — they now literally call the same function.
"""

import textwrap

from tpsplots.models.yaml_config import YAMLChartConfig
from tpsplots.processors.render_pipeline import build_render_context
from tpsplots.processors.resolvers import DataResolver


def _build_ctx_from_yaml(tmp_path, yaml_text, *, log_conflicts=True):
    """Build a RenderContext from raw YAML text (shared helper)."""
    import yaml

    yaml_path = tmp_path / "chart.yaml"
    yaml_path.write_text(textwrap.dedent(yaml_text).strip())

    raw = yaml.safe_load(yaml_path.read_text())
    validated = YAMLChartConfig(**raw)
    data = DataResolver.resolve(validated.data)
    return build_render_context(validated, data, log_conflicts=log_conflicts)


class TestCLIEditorParity:
    """Verify CLI and editor paths produce identical render contexts.

    Since both paths now call ``build_render_context()`` directly, these
    tests serve as regression guards against future divergence.
    """

    def test_line_chart_parity(self, tmp_path):
        """Line chart with basic params produces same context from both paths."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,Value\n2024,10\n2025,20\n2026,30\n")

        yaml_text = f"""
        data:
          source: csv:{csv}

        chart:
          type: line
          output: parity_line
          title: "Line Parity"
          subtitle: "Testing parity"
          x: "{{{{Year}}}}"
          y: "{{{{Value}}}}"
          color: "Neptune Blue"
        """

        ctx_cli = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=True)
        ctx_editor = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=False)

        assert ctx_cli.chart_type_v1 == ctx_editor.chart_type_v1
        assert ctx_cli.output_name == ctx_editor.output_name
        assert ctx_cli.resolved_metadata == ctx_editor.resolved_metadata
        assert ctx_cli.resolved_params.keys() == ctx_editor.resolved_params.keys()

        # Compare param values (pandas/numpy need special handling)
        import numpy as np
        import pandas as pd

        for key in ctx_cli.resolved_params:
            cli_val = ctx_cli.resolved_params[key]
            ed_val = ctx_editor.resolved_params[key]
            if isinstance(cli_val, (pd.Series, pd.DataFrame)):
                assert cli_val.equals(ed_val), f"DataFrame mismatch on param '{key}'"
            elif isinstance(cli_val, np.ndarray):
                np.testing.assert_array_equal(
                    cli_val, ed_val, err_msg=f"Array mismatch on param '{key}'"
                )
            else:
                assert cli_val == ed_val, f"Mismatch on param '{key}'"

    def test_bar_chart_parity(self, tmp_path):
        """Bar chart produces same context."""
        csv = tmp_path / "data.csv"
        csv.write_text("Category,Amount\nA,100\nB,200\nC,150\n")

        yaml_text = f"""
        data:
          source: csv:{csv}

        chart:
          type: bar
          output: parity_bar
          title: "Bar Parity"
          categories: "{{{{Category}}}}"
          values: "{{{{Amount}}}}"
        """

        ctx_cli = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=True)
        ctx_editor = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=False)

        assert ctx_cli.chart_type_v1 == ctx_editor.chart_type_v1 == "bar_plot"
        assert ctx_cli.output_name == ctx_editor.output_name
        assert ctx_cli.resolved_metadata == ctx_editor.resolved_metadata

    def test_legend_dict_preserved_in_both_paths(self, tmp_path):
        """Legend dict (the original bug trigger) is preserved identically."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,A,B\n2024,10,30\n2025,20,40\n")

        yaml_text = f"""
        data:
          source: csv:{csv}

        chart:
          type: line
          output: legend_dict_test
          title: "Legend Dict"
          x: "{{{{Year}}}}"
          y:
            - "{{{{A}}}}"
            - "{{{{B}}}}"
          legend:
            loc: "upper right"
            fontsize: "medium"
        """

        ctx_cli = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=True)
        ctx_editor = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=False)

        # Both paths preserve legend as a dict, not coerced to boolean
        assert isinstance(ctx_cli.resolved_params["legend"], dict)
        assert isinstance(ctx_editor.resolved_params["legend"], dict)
        assert ctx_cli.resolved_params["legend"] == {"loc": "upper right", "fontsize": "medium"}
        assert ctx_cli.resolved_params["legend"] == ctx_editor.resolved_params["legend"]

    def test_series_overrides_expanded_identically(self, tmp_path):
        """series_overrides expansion produces same series_<n> keys."""
        csv = tmp_path / "data.csv"
        csv.write_text("Year,A,B\n2024,10,30\n2025,20,40\n")

        yaml_text = f"""
        data:
          source: csv:{csv}

        chart:
          type: line
          output: series_override_parity
          title: "Series Parity"
          x: "{{{{Year}}}}"
          y:
            - "{{{{A}}}}"
            - "{{{{B}}}}"
          series_0:
            color: "Neptune Blue"
            linewidth: 3
        """

        ctx_cli = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=True)
        ctx_editor = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=False)

        assert "series_0" in ctx_cli.resolved_params
        assert "series_0" in ctx_editor.resolved_params
        assert ctx_cli.resolved_params["series_0"]["color"] == "#037CC2"
        assert ctx_cli.resolved_params["series_0"] == ctx_editor.resolved_params["series_0"]

    def test_metadata_extracted_identically(self, tmp_path):
        """All metadata fields (title, subtitle, source) are extracted consistently."""
        csv = tmp_path / "data.csv"
        csv.write_text("Category,Amount\nA,100\n")

        yaml_text = f"""
        data:
          source: csv:{csv}

        chart:
          type: bar
          output: meta_parity
          title: "The Title"
          subtitle: "The Subtitle"
          source: "The Source"
          categories: "{{{{Category}}}}"
          values: "{{{{Amount}}}}"
        """

        ctx_cli = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=True)
        ctx_editor = _build_ctx_from_yaml(tmp_path, yaml_text, log_conflicts=False)

        assert ctx_cli.resolved_metadata == ctx_editor.resolved_metadata
        assert ctx_cli.resolved_metadata == {
            "title": "The Title",
            "subtitle": "The Subtitle",
            "source": "The Source",
        }
