"""Tests for ChartView base behavior."""

from pathlib import Path

import matplotlib.pyplot as plt

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


class SingleDeviceChartView(ChartView):
    """Minimal view for testing create_figure."""

    def __init__(self, outdir):
        super().__init__(outdir=outdir, style_file=None)
        self.create_calls = []

    def _create_chart(self, metadata, style, **kwargs):
        self.create_calls.append(style["type"])
        return object()


def test_create_figure_renders_single_device(tmp_path):
    """create_figure should only invoke _create_chart once for the requested device."""
    view = SingleDeviceChartView(outdir=tmp_path)

    fig = view.create_figure(metadata={"title": "Test"}, device="mobile", legend=True)

    assert fig is not None
    assert view.create_calls == ["mobile"]


def test_create_figure_defaults_to_desktop(tmp_path):
    """create_figure with no device argument should render desktop."""
    view = SingleDeviceChartView(outdir=tmp_path)

    view.create_figure(metadata={"title": "Test"})

    assert view.create_calls == ["desktop"]


def test_create_figure_ignores_export_data(tmp_path):
    """create_figure should silently discard export_data without error."""
    view = SingleDeviceChartView(outdir=tmp_path)

    fig = view.create_figure(metadata={}, export_data=object())

    assert fig is not None
    assert len(view.create_calls) == 1


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


def test_add_logo_adds_vector_path_patch(tmp_path, monkeypatch):
    """_add_logo should add a vector PathPatch to the figure."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    from tpsplots.views import logo

    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(16, 10), dpi=300)

    # Monkeypatch the cached path with a minimal triangle.
    triangle = MplPath(
        [(0.0, 0.0), (100.0, 0.0), (50.0, 100.0), (0.0, 0.0)],
        [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.CLOSEPOLY],
    )
    monkeypatch.setattr(logo, "_cached_path", triangle)

    view._add_logo(fig, ChartView.DESKTOP)

    patches = [c for c in fig.get_children() if isinstance(c, PathPatch)]
    assert len(patches) == 1
    # Facecolor should match the logo grey (#545454 ≈ 0.329)
    fc = patches[0].get_facecolor()
    assert abs(fc[0] - 0.329) < 0.01
    plt.close(fig)
