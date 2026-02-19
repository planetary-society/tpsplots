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


# ── _center_axes_vertically tests ──────────────────────────────────


def _measure_gaps(fig, header_height, footer_height):
    """Return (top_gap, bottom_gap) between axes visual extent and reference lines."""
    renderer = fig.canvas.get_renderer()
    y_mins, y_maxes = [], []
    for ax in fig.get_axes():
        if not ax.get_visible():
            continue
        bbox = ax.get_tightbbox(renderer)
        if bbox is not None:
            fig_bbox = bbox.transformed(fig.transFigure.inverted())
            y_mins.append(fig_bbox.y0)
            y_maxes.append(fig_bbox.y1)
    ref_top = 1.0 - header_height
    ref_bottom = footer_height / 2.0 if footer_height > 0 else 0.0
    return ref_top - max(y_maxes), min(y_mins) - ref_bottom


def test_center_axes_equalizes_gaps(tmp_path):
    """After centering, top and bottom gaps should be roughly equal."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.12, 0.08

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    # Large tick labels on bottom create asymmetry
    ax.set_yticks([0, 50, 100])
    ax.set_yticklabels(["$0B", "$50B", "$100B"], fontsize=14)
    ax.set_xlabel("Fiscal Year", fontsize=12)
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    top_before, bottom_before = _measure_gaps(fig, header_height, footer_height)
    # There should be meaningful asymmetry before centering
    gap_diff_before = abs(bottom_before - top_before)

    view._center_axes_vertically(fig, header_height, footer_height)

    top_after, bottom_after = _measure_gaps(fig, header_height, footer_height)
    gap_diff_after = abs(bottom_after - top_after)

    # Centering should reduce the gap difference
    assert gap_diff_after <= gap_diff_before + 0.001
    # Gaps should be close to equal (within 1% of figure height)
    assert gap_diff_after < 0.01
    plt.close(fig)


def test_center_axes_noop_when_already_centered(tmp_path):
    """Centering should be a no-op when gaps are within threshold."""
    view = ChartView(outdir=tmp_path, style_file=None)
    # With no header/footer, ref_top=1.0 and ref_bottom=0.0, so tight_layout
    # already centers the axes symmetrically → shift should be below threshold.
    header_height, footer_height = 0, 0

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    ax.axis("off")
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    pos_before = ax.get_position()
    view._center_axes_vertically(fig, header_height, footer_height)
    pos_after = ax.get_position()

    # Position should not change (shift < threshold)
    assert abs(pos_after.y0 - pos_before.y0) < 0.005
    plt.close(fig)


def test_center_axes_skips_hidden_axes(tmp_path):
    """Hidden axes should not influence centering calculations."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.12, 0.08

    fig = plt.figure(figsize=(8, 9), dpi=150)
    ax1 = fig.add_subplot(111)
    ax1.set_yticks([0, 100])

    # Add a hidden axes placed far off
    ax_hidden = fig.add_axes([0.1, 0.95, 0.8, 0.04], visible=False)
    ax_hidden.set_yticks([0, 1])

    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    pos_hidden_before = ax_hidden.get_position()

    view._center_axes_vertically(fig, header_height, footer_height)

    # Hidden axes should not move
    pos_hidden_after = ax_hidden.get_position()
    assert abs(pos_hidden_after.y0 - pos_hidden_before.y0) < 1e-9
    plt.close(fig)


def test_center_axes_empty_figure(tmp_path):
    """Centering an empty figure should not raise."""
    view = ChartView(outdir=tmp_path, style_file=None)
    fig = plt.figure(figsize=(8, 9))

    # No axes at all — should be a silent no-op
    view._center_axes_vertically(fig, 0.12, 0.08)
    plt.close(fig)


def test_center_axes_respects_zone_bounds(tmp_path):
    """Axes visual extent should stay within the tight_layout zone after centering."""
    view = ChartView(outdir=tmp_path, style_file=None)
    header_height, footer_height = 0.15, 0.10

    fig, ax = plt.subplots(figsize=(8, 9), dpi=150)
    ax.set_yticks(range(0, 1001, 100))
    ax.set_yticklabels([f"${v}B" for v in range(0, 1001, 100)], fontsize=12)
    ax.set_xlabel("Year", fontsize=14, labelpad=20)
    fig.tight_layout(rect=[0, footer_height, 1, 1 - header_height])

    view._center_axes_vertically(fig, header_height, footer_height)

    # Verify axes data-area position stays within zone
    zone_top = 1.0 - header_height
    zone_bottom = footer_height
    for a in fig.get_axes():
        pos = a.get_position()
        assert pos.y0 >= zone_bottom - 0.01, f"Axes bottom {pos.y0} below zone {zone_bottom}"
        assert pos.y1 <= zone_top + 0.01, f"Axes top {pos.y1} above zone {zone_top}"
    plt.close(fig)


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
