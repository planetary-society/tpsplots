"""Tests for the text editor preview feature."""

import textwrap
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from tpsplots.cli import app

runner = CliRunner()


def _write_minimal_chart_yaml(tmp_path: Path) -> Path:
    """Create a minimal chart YAML and CSV fixture."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")

    yaml_path = tmp_path / "chart.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            f"""
            data:
              source: csv:{csv_path}

            chart:
              type: line
              output: preview_chart
              title: "Original Title"
              subtitle: "Original Subtitle"
              source: "Original Source"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
            """
        ).strip(),
        encoding="utf-8",
    )
    return yaml_path


def test_textedit_help():
    """CLI should expose a dedicated textedit command."""
    result = runner.invoke(app, ["textedit", "--help"])
    assert result.exit_code == 0
    assert "textedit" in result.stdout.lower()
    assert "--host" in result.stdout
    assert "--port" in result.stdout


def test_textedit_dispatches_to_server(monkeypatch, tmp_path):
    """textedit command should delegate to a server launcher function."""
    yaml_path = _write_minimal_chart_yaml(tmp_path)

    from tpsplots.commands import textedit as textedit_module

    called = {}

    def fake_start_textedit_server(yaml_file, host, port, open_browser):
        called["yaml_file"] = yaml_file
        called["host"] = host
        called["port"] = port
        called["open_browser"] = open_browser

    monkeypatch.setattr(textedit_module, "start_textedit_server", fake_start_textedit_server)

    result = runner.invoke(
        app,
        [
            "textedit",
            str(yaml_path),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--no-open-browser",
        ],
    )

    assert result.exit_code == 0
    assert called["yaml_file"] == yaml_path
    assert called["host"] == "127.0.0.1"
    assert called["port"] == 0
    assert called["open_browser"] is False


def test_textedit_session_renders_svg_without_writing_chart_files(tmp_path):
    """Session preview should return SVG output without creating chart files on disk."""
    yaml_path = _write_minimal_chart_yaml(tmp_path)
    outdir = tmp_path / "charts"

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_path, outdir=outdir)
    svg = session.render_svg(
        device="desktop",
        title="Edited Title",
        subtitle="Edited Subtitle",
        source="Edited Source",
    )

    assert "<svg" in svg
    assert "Edited Title" in svg
    assert not list(outdir.glob("*.svg"))
    assert not list(outdir.glob("*.png"))
    assert not list(outdir.glob("*.pptx"))


def test_textedit_session_save_updates_source_yaml(tmp_path):
    """Saving in a session should update title/subtitle/source in YAML."""
    yaml_path = _write_minimal_chart_yaml(tmp_path)

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_path, outdir=tmp_path / "charts")
    session.save_text(
        title="Saved Title",
        subtitle="Saved Subtitle",
        source="Saved Source",
    )

    saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert saved["chart"]["title"] == "Saved Title"
    assert saved["chart"]["subtitle"] == "Saved Subtitle"
    assert saved["chart"]["source"] == "Saved Source"
    assert saved["chart"]["x"] == "{{Year}}"
    assert saved["chart"]["y"] == "{{Value}}"


def test_textedit_session_save_can_clear_optional_fields(tmp_path):
    """Saving blank optional fields should remove them from chart metadata."""
    yaml_path = _write_minimal_chart_yaml(tmp_path)

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_path, outdir=tmp_path / "charts")
    session.save_text(title="Retained Title", subtitle="", source="")
    saved = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert saved["chart"]["title"] == "Retained Title"
    assert "subtitle" not in saved["chart"]
    assert "source" not in saved["chart"]


def test_textedit_session_save_rejects_empty_title(tmp_path):
    """Saving without a title should fail because chart.title is required."""
    yaml_path = _write_minimal_chart_yaml(tmp_path)

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_path, outdir=tmp_path / "charts")
    with pytest.raises(ValueError, match="title"):
        session.save_text(title="   ", subtitle="any", source="any")


def test_textedit_session_save_preserves_order_and_comments(tmp_path):
    """Saving should only touch chart text keys and preserve all other content verbatim."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("Year,Value\n2024,10\n2025,20\n", encoding="utf-8")

    yaml_path = tmp_path / "chart.yaml"
    original = textwrap.dedent(
        f"""
        # top-level comment
        data:
          # data source comment
          source: csv:{csv_path}
          params:
            columns:
              - Year
              - Value

        chart:
          # chart type comment
          type: line
          output: preserved_chart
          title: "Old Title"
          subtitle: "Old Subtitle"
          source: "Old Source"
          x: "{{{{Year}}}}"
          y: "{{{{Value}}}}"
          legend: false # keep this
        """
    ).lstrip()
    yaml_path.write_text(original, encoding="utf-8")

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_path, outdir=tmp_path / "charts")
    session.save_text(title="New Title", subtitle="New Subtitle", source="New Source")

    updated = yaml_path.read_text(encoding="utf-8")

    # Confirm target fields changed.
    assert 'title: "New Title"' in updated
    assert 'subtitle: "New Subtitle"' in updated
    assert 'source: "New Source"' in updated

    # Confirm comments still exist.
    assert "# top-level comment" in updated
    assert "# data source comment" in updated
    assert "# chart type comment" in updated
    assert "legend: false # keep this" in updated

    # Everything except the three text lines in chart should remain unchanged.
    def strip_chart_text_lines(content: str) -> list[str]:
        lines = content.splitlines()
        output_lines = []
        inside_chart = False
        for line in lines:
            if line.startswith("chart:"):
                inside_chart = True
                output_lines.append(line)
                continue
            if inside_chart and line.startswith("  title:"):
                continue
            if inside_chart and line.startswith("  subtitle:"):
                continue
            if inside_chart and line.startswith("  source:"):
                continue
            output_lines.append(line)
        return output_lines

    assert strip_chart_text_lines(updated) == strip_chart_text_lines(original)
