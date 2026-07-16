"""Tests for the ``tpsplots animate`` CLI command.

All internals are monkeypatched — no test in this module encodes a single frame.
``resolve_ffmpeg`` is either no-op'd (so the command reaches its per-file loop)
or forced to raise, and ``animate_yaml`` is stubbed except in the
non-animatable-type case, where the real type gate runs before any data fetch.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tpsplots.animation.encoder import FFmpegUnavailableError
from tpsplots.cli import app

runner = CliRunner()


@pytest.fixture
def ffmpeg_ok(monkeypatch):
    """No-op ffmpeg resolution so the command reaches its per-file loop."""
    monkeypatch.setattr("tpsplots.commands.animate.resolve_ffmpeg", lambda: "ffmpeg")


def test_animate_help_lists_key_options():
    """`animate --help` exits 0 and documents formats, fps, and quality."""
    result = runner.invoke(app, ["animate", "--help"])

    assert result.exit_code == 0
    out = result.output.lower()
    assert "format" in out
    assert "fps" in out
    assert "quality" in out


def test_missing_ffmpeg_exits_2_with_install_hint(monkeypatch):
    """No ffmpeg binary is an environment error (exit 2) with an install hint."""

    def _raise():
        raise FFmpegUnavailableError(
            "ffmpeg not found. Install with: pip install 'tpsplots[animate]'"
        )

    monkeypatch.setattr("tpsplots.commands.animate.resolve_ffmpeg", _raise)

    result = runner.invoke(app, ["animate", "chart.yaml"])

    assert result.exit_code == 2
    assert "tpsplots[animate]" in result.output


def test_non_animatable_type_reports_and_fails(tmp_path, ffmpeg_ok):
    """A donut is rejected with a clear "not animatable" message (exit 1)."""
    csv = tmp_path / "data.csv"
    csv.write_text("x\n1\n", encoding="utf-8")
    yaml_path = tmp_path / "donut.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            f"""
            data:
              source: csv:{csv}
            chart:
              type: donut
              output: my_donut
              title: "Donut"
              values: [1, 2, 3]
              labels: [A, B, C]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["animate", str(yaml_path), "-o", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "not animatable" in result.output
    assert "Summary: 0 succeeded, 1 failed" in result.output


def test_success_path_calls_animate_yaml_per_file(tmp_path, monkeypatch, ffmpeg_ok):
    """Each YAML triggers one animate_yaml call; unset flags pass through as None."""
    calls: list[dict] = []

    def fake_animate_yaml(yaml_path, outdir, on_frame=None, **overrides):
        calls.append({"yaml_path": Path(yaml_path), "outdir": outdir, "overrides": overrides})
        stem = Path(yaml_path).stem
        return [outdir / f"{stem}_square.mp4", outdir / f"{stem}_square_poster.png"]

    monkeypatch.setattr("tpsplots.commands.animate.animate_yaml", fake_animate_yaml)

    yaml_1 = tmp_path / "one.yaml"
    yaml_2 = tmp_path / "two.yaml"
    yaml_1.write_text("chart: {}\n", encoding="utf-8")
    yaml_2.write_text("chart: {}\n", encoding="utf-8")

    result = runner.invoke(app, ["animate", str(yaml_1), str(yaml_2), "-o", str(tmp_path / "out")])

    assert result.exit_code == 0
    assert len(calls) == 2
    assert {c["yaml_path"].name for c in calls} == {"one.yaml", "two.yaml"}
    # The precedence guard: an unset flag is None so YAML/defaults win downstream.
    for call in calls:
        assert call["overrides"]["fps"] is None
        assert call["overrides"]["formats"] is None
        assert call["overrides"]["quality"] is None
        assert call["overrides"]["scale"] is None
    assert "Summary: 2 succeeded, 0 failed" in result.output


def test_no_yaml_files_found_exits_2(tmp_path, ffmpeg_ok):
    """An input with no YAML files is a usage error (exit 2)."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = runner.invoke(app, ["animate", str(empty_dir)])

    assert result.exit_code == 2


def test_format_all_passes_through(tmp_path, monkeypatch, ffmpeg_ok):
    """`--format all` forwards formats=["all"] to animate_yaml."""
    captured: list[dict] = []

    def fake_animate_yaml(yaml_path, outdir, on_frame=None, **overrides):
        captured.append(overrides)
        return []

    monkeypatch.setattr("tpsplots.commands.animate.animate_yaml", fake_animate_yaml)

    yaml_path = tmp_path / "chart.yaml"
    yaml_path.write_text("chart: {}\n", encoding="utf-8")

    result = runner.invoke(
        app, ["animate", str(yaml_path), "--format", "all", "-o", str(tmp_path / "out")]
    )

    assert result.exit_code == 0
    assert captured[0]["formats"] == ["all"]
