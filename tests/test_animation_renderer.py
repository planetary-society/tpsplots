"""Tests for the animate orchestrator (no real ffmpeg / no real encoding).

``resolve_ffmpeg`` and ``write_mp4`` are stubbed to no-ops, and the animator is
faked via a patched ``get_animator`` so these tests exercise renderer
orchestration (type gating, figsize/dpi stripping, output naming, scale, draft
fps) without encoding a single frame.
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

import tpsplots.animation.renderer as renderer
from tpsplots.animation.animators import UnsupportedChartAnimation
from tpsplots.animation.renderer import animate_yaml
from tpsplots.processors.resolvers import DataResolver
from tpsplots.views.chart_view import ChartView


def _write_yaml(tmp_path, body: str) -> Path:
    path = tmp_path / "chart.yaml"
    path.write_text(textwrap.dedent(body).strip() + "\n")
    return path


def _line_yaml(tmp_path, *, output="anim_line", extra_lines: str = "") -> Path:
    csv = tmp_path / "data.csv"
    csv.write_text("Year,Value\n2020,10\n2021,20\n2022,30\n")
    # Dedent the base first so chart fields sit at 2-space indent, then append
    # any extra chart fields at the same indent (appending before dedent would
    # corrupt the block structure).
    body = textwrap.dedent(
        f"""
        data:
          source: csv:{csv}
        chart:
          type: line
          output: {output}
          title: "Anim Line"
          x: "{{{{Year}}}}"
          y: "{{{{Value}}}}"
        """
    ).strip()
    if extra_lines:
        body += "\n" + textwrap.indent(textwrap.dedent(extra_lines).strip(), "  ")
    return _write_yaml(tmp_path, body)


class _Recorders:
    def __init__(self):
        self.create_calls: list[dict] = []
        self.animator_records: list[dict] = []
        self.write_calls: list[dict] = []


def _patch_common(monkeypatch) -> _Recorders:
    """Stub ffmpeg/encoding and fake the animator; spy on figure creation."""
    rec = _Recorders()
    monkeypatch.setattr(renderer, "resolve_ffmpeg", lambda: "ffmpeg")

    def spy_write_mp4(fig, animator, out_path, *, fps, quality, on_frame=None):
        rec.write_calls.append({"out_path": out_path, "fps": fps, "quality": quality})

    monkeypatch.setattr(renderer, "write_mp4", spy_write_mp4)

    class FakeAnimator:
        def __init__(self, fig, anim, choreo, expected_px=None):
            rec.animator_records.append(
                {"expected_px": expected_px, "anim": anim, "choreo": choreo}
            )

        def prepare(self):
            pass

        def finalize(self):
            pass

    monkeypatch.setattr(renderer, "get_animator", lambda chart_type_v1: FakeAnimator)

    def spy_create_figure(self, metadata, device="desktop", **kwargs):
        rec.create_calls.append({"device": device, "metadata": metadata, "kwargs": kwargs})
        return plt.figure()

    monkeypatch.setattr(ChartView, "create_figure", spy_create_figure)
    return rec


def test_unsupported_type_rejected_before_data_fetch(tmp_path, monkeypatch):
    """A donut is rejected before DataResolver ever runs."""
    monkeypatch.setattr(renderer, "resolve_ffmpeg", lambda: "ffmpeg")

    def _boom(*args, **kwargs):
        raise AssertionError("DataResolver.resolve must not be called for a rejected type")

    monkeypatch.setattr(DataResolver, "resolve", staticmethod(_boom))

    csv = tmp_path / "data.csv"
    csv.write_text("x\n1\n")
    yaml_path = _write_yaml(
        tmp_path,
        f"""
        data:
          source: csv:{csv}
        chart:
          type: donut
          output: my_donut
          title: "Donut"
          values: [1, 2, 3]
          labels: [A, B, C]
        """,
    )

    with pytest.raises(UnsupportedChartAnimation):
        animate_yaml(yaml_path, outdir=tmp_path)


def test_yaml_figsize_and_dpi_stripped_with_warning(tmp_path, monkeypatch, caplog):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path, extra_lines="figsize: [16, 10]\ndpi: 200")

    with caplog.at_level(logging.WARNING, logger="tpsplots.animation.renderer"):
        animate_yaml(yaml_path, outdir=tmp_path)

    kwargs = rec.create_calls[0]["kwargs"]
    assert "figsize" not in kwargs
    assert "dpi" not in kwargs  # scale == 1, so dpi is not re-injected either
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "figsize" in messages
    assert "dpi" in messages


def test_output_naming_default_square(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path, output="myplot")

    outputs = animate_yaml(yaml_path, outdir=tmp_path)

    assert outputs == [
        tmp_path / "myplot_square.mp4",
        tmp_path / "myplot_square_poster.png",
    ]
    assert (tmp_path / "myplot_square_poster.png").exists()


def test_scale_doubles_expected_px_and_dpi(tmp_path, monkeypatch):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path)

    animate_yaml(yaml_path, outdir=tmp_path, scale=2)

    # VIDEO_SQUARE is 7.2in @ 150dpi = 1080px; scale 2 -> 2160px, dpi 300.
    assert rec.animator_records[0]["expected_px"] == (2160, 2160)
    assert rec.create_calls[0]["kwargs"]["dpi"] == 300


def test_scale_one_keeps_base_dims(tmp_path, monkeypatch):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path)

    animate_yaml(yaml_path, outdir=tmp_path)

    assert rec.animator_records[0]["expected_px"] == (1080, 1080)
    # scale == 1 -> dpi is not injected into params (device style supplies it).
    assert "dpi" not in rec.create_calls[0]["kwargs"]


def test_draft_quality_forces_fps_le_30(tmp_path, monkeypatch):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path)

    animate_yaml(yaml_path, outdir=tmp_path, quality="draft")

    assert rec.write_calls[0]["fps"] == 30
    assert rec.write_calls[0]["quality"] == "draft"


def test_high_quality_keeps_default_fps(tmp_path, monkeypatch):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path)

    animate_yaml(yaml_path, outdir=tmp_path)

    assert rec.write_calls[0]["fps"] == 60


def test_all_formats_produce_paired_outputs(tmp_path, monkeypatch):
    rec = _patch_common(monkeypatch)
    yaml_path = _line_yaml(tmp_path, output="multi")

    outputs = animate_yaml(yaml_path, outdir=tmp_path, formats=("square", "landscape"))

    assert outputs == [
        tmp_path / "multi_square.mp4",
        tmp_path / "multi_square_poster.png",
        tmp_path / "multi_landscape.mp4",
        tmp_path / "multi_landscape_poster.png",
    ]
    # Devices resolved per format.
    assert [c["device"] for c in rec.create_calls] == ["video_square", "video_landscape"]
