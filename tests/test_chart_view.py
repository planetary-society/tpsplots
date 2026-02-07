"""Tests for ChartView base behavior."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import tpsplots.views.chart_view as chart_view_module
from tpsplots.views.chart_view import ChartView


class MutatingChartView(ChartView):
    """Minimal view that intentionally mutates nested kwargs in _create_chart."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)
        self.legend_snapshots = []

    def _create_chart(self, metadata, style, **kwargs):
        legend = kwargs["legend"]
        legend["fontsize"] = style["legend_size"]
        legend.setdefault("rendered_for", []).append(style["type"])
        self.legend_snapshots.append(legend)
        return object()

    def _save_chart(self, *_args, **_kwargs):
        return []


def test_generate_chart_isolates_nested_kwargs_between_renders(tmp_path):
    """Desktop and mobile renders should not share nested kwargs state."""
    view = MutatingChartView(outdir=tmp_path)
    legend = {"ncol": 4}

    view.generate_chart(metadata={}, stem="test", legend=legend)

    # Caller-supplied kwargs should not be mutated by chart generation.
    assert legend == {"ncol": 4}

    desktop_legend, mobile_legend = view.legend_snapshots
    assert desktop_legend["rendered_for"] == ["desktop"]
    assert mobile_legend["rendered_for"] == ["mobile"]


class FileTrackingChartView(ChartView):
    """Minimal view that returns deterministic file paths for save/export."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)

    def _create_chart(self, metadata, style, **kwargs):
        return object()

    def _save_chart(self, fig, filename, metadata, create_pptx=False):
        files = [
            str(self.outdir / f"{filename}.svg"),
            str(self.outdir / f"{filename}.png"),
        ]
        if create_pptx:
            files.append(str(self.outdir / f"{filename.replace('_desktop', '')}.pptx"))
        return files

    def _export_csv(self, df, metadata, stem):
        return Path(self.outdir / f"{stem}.csv")


def test_generate_chart_reports_generated_files(tmp_path):
    """generate_chart should include all output file paths in result['files']."""
    view = FileTrackingChartView(outdir=tmp_path)
    result = view.generate_chart(metadata={}, stem="budget", export_data=object())

    expected = [
        str(tmp_path / "budget_desktop.svg"),
        str(tmp_path / "budget_desktop.png"),
        str(tmp_path / "budget.pptx"),
        str(tmp_path / "budget_mobile.svg"),
        str(tmp_path / "budget_mobile.png"),
        str(tmp_path / "budget.csv"),
    ]
    assert result["files"] == expected


def test_save_chart_uses_figure_dpi_for_svg_and_png(tmp_path, monkeypatch):
    """_save_chart should rely on figure DPI as the single source of truth."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure()
    save_calls: list[tuple[str, str | None, int | None]] = []

    def fake_savefig(path, **kwargs):
        save_calls.append((str(path), kwargs.get("format"), kwargs.get("dpi")))

    monkeypatch.setattr(fig, "savefig", fake_savefig)
    view._save_chart(fig, "dpi_test", metadata={}, create_pptx=False)

    assert len(save_calls) == 2
    assert save_calls[0][1] == "svg"
    assert save_calls[0][2] == "figure"
    assert save_calls[1][1] == "png"
    assert save_calls[1][2] == "figure"


def test_add_logo_uses_non_smoothed_raster_settings(tmp_path, monkeypatch):
    """_add_logo should avoid smoothing that blurs thin logo details."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure()
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    logo_path = image_dir / "TPS_Logo_1Line-Black-Cutout.png"

    # Tiny synthetic RGBA logo file for deterministic testing.
    logo = np.zeros((12, 120, 4), dtype=np.float32)
    logo[:, :, 3] = 1.0
    plt.imsave(logo_path, logo)

    captured_kwargs: dict = {}
    real_offset_image = chart_view_module.OffsetImage

    def capture_offset_image(arr, **kwargs):
        captured_kwargs.update(kwargs)
        return real_offset_image(arr, **kwargs)

    monkeypatch.setattr(chart_view_module, "IMAGES_DIR", image_dir)
    monkeypatch.setattr(chart_view_module, "OffsetImage", capture_offset_image)

    view._add_logo(fig, {"logo_zoom": 0.08, "logo_x": 0.01, "logo_y": 0.005})

    assert captured_kwargs["resample"] is False
    assert captured_kwargs["interpolation"] == "none"
