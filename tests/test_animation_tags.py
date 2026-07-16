"""Tests for the inert animation tagging layer (``tpsplots.views.anim_tags``).

These verify that views stamp their data artists with the expected roles/indices
at draw time, that tagging is completely inert for static SVG output, and that
importing views never eagerly pulls in the animation/encoding stack.

Figures are built in memory via ``ChartView.create_figure`` (no files written).
"""

import subprocess
import sys
from collections import Counter
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

from tpsplots.views.anim_tags import Roles, iter_tagged
from tpsplots.views.bar_chart import BarChartView
from tpsplots.views.grouped_bar_chart import GroupedBarChartView
from tpsplots.views.line_chart import LineChartView
from tpsplots.views.lollipop_chart import LollipopChartView
from tpsplots.views.stacked_bar_chart import StackedBarChartView


def _tags(fig):
    """Return the list of Tag objects carried by artists in ``fig``."""
    return [tag for tag, _ in iter_tagged(fig)]


def _indices(fig, role):
    """Return the sorted global indices of all tags with the given role."""
    return sorted(tag.index for tag in _tags(fig) if tag.role == role)


# ── Line ───────────────────────────────────────────────────────────


def test_line_chart_tags_series_endpoints_and_labels(tmp_path):
    """Two-series line chart tags 2 series, 2 endpoints, 2 series labels."""
    view = LineChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        x=[1, 2, 3],
        y=[[1, 2, 3], [2, 3, 4]],
        direct_line_labels={"end_point": True},
        legend=False,
    )

    assert _indices(fig, Roles.SERIES) == [0, 1]
    assert _indices(fig, Roles.ENDPOINT) == [0, 1]
    assert _indices(fig, Roles.SERIES_LABEL) == [0, 1]


# ── Twinx (dual y-axis) ────────────────────────────────────────────


def test_twinx_series_indices_are_contiguous(tmp_path):
    """Right-axis series continue the global index after the left-axis series."""
    view = LineChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        x=[1, 2, 3],
        y=[[1, 2, 3], [2, 3, 4]],  # 2 left-axis series → indices 0, 1
        y_right=[[5, 6, 7]],  # 1 right-axis series → index 2
        direct_line_labels={"end_point": True},
        legend=False,
    )

    # Global indices span left (0..n-1) then right (continuing at n), contiguous.
    assert _indices(fig, Roles.SERIES) == [0, 1, 2]
    assert _indices(fig, Roles.ENDPOINT) == [0, 1, 2]
    assert _indices(fig, Roles.SERIES_LABEL) == [0, 1, 2]


# ── Bar ────────────────────────────────────────────────────────────


def test_bar_chart_tags_bars_and_value_labels(tmp_path):
    """N categories → N BAR tags (with orient/baseline meta) and N VALUE_LABEL."""
    values = [3, 5, 2]
    view = BarChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=["A", "B", "C"],
        values=values,
        show_values=True,
        legend=False,
    )

    bar_tags = [t for t in _tags(fig) if t.role == Roles.BAR]
    assert _indices(fig, Roles.BAR) == list(range(len(values)))
    assert _indices(fig, Roles.VALUE_LABEL) == list(range(len(values)))

    # Every bar carries orientation + baseline meta for the animator.
    for tag in bar_tags:
        assert tag.meta["orient"] == "v"
        assert tag.meta["baseline"] == 0


def test_horizontal_bar_tags_carry_orientation(tmp_path):
    """Horizontal bars are tagged with orient='h'."""
    view = BarChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=["A", "B"],
        values=[3, 5],
        orientation="horizontal",
        legend=False,
    )

    bar_tags = [t for t in _tags(fig) if t.role == Roles.BAR]
    assert len(bar_tags) == 2
    assert all(t.meta["orient"] == "h" for t in bar_tags)


# ── Stacked bar ────────────────────────────────────────────────────


def test_stacked_bar_segment_index_layer_pairs(tmp_path):
    """BAR_SEGMENT count = categories x columns with correct (index, layer) pairs."""
    categories = ["A", "B", "C"]
    values = {"X": [1, 2, 3], "Y": [4, 5, 6]}  # 2 columns (layers)
    view = StackedBarChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=categories,
        values=values,
        legend=False,
    )

    seg_pairs = {
        (tag.index, tag.meta["layer"]) for tag in _tags(fig) if tag.role == Roles.BAR_SEGMENT
    }
    expected = {(j, i) for j in range(len(categories)) for i in range(len(values))}
    assert seg_pairs == expected
    assert len(seg_pairs) == len(categories) * len(values)


# ── Lollipop ───────────────────────────────────────────────────────


def test_lollipop_tags_stems_and_end_markers(tmp_path):
    """STEM + END_MARKER counts match category count; stems carry numeric start/end."""
    categories = ["A", "B"]
    start_values = [1, 2]
    end_values = [5, 6]
    view = LollipopChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=categories,
        start_values=start_values,
        end_values=end_values,
    )

    roles = Counter(tag.role for tag in _tags(fig))
    assert roles[Roles.STEM] == len(categories)
    assert roles[Roles.END_MARKER] == len(categories)

    # The start marker stays untagged (static): each category draws start + end
    # scatter collections, but only the end markers carry tags.
    assert len(fig.axes[0].collections) == 2 * len(categories)

    stem_tags = sorted((tag for tag in _tags(fig) if tag.role == Roles.STEM), key=lambda t: t.index)
    assert [t.index for t in stem_tags] == [0, 1]
    for tag, start, end in zip(stem_tags, start_values, end_values, strict=True):
        assert isinstance(tag.meta["start"], float)
        assert isinstance(tag.meta["end"], float)
        assert tag.meta["start"] == float(start)
        assert tag.meta["end"] == float(end)


# ── Grouped bar ────────────────────────────────────────────────────


def test_grouped_bar_tags_carry_index_and_group(tmp_path):
    """Grouped bars tag each rect with its category index and group."""
    view = GroupedBarChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=["A", "B"],
        groups=[
            {"label": "G1", "values": [1, 2]},
            {"label": "G2", "values": [3, 4]},
        ],
        show_values=True,
    )

    bar_meta = {
        (tag.index, tag.meta["group"], tag.meta["layer"])
        for tag in _tags(fig)
        if tag.role == Roles.BAR
    }
    expected = {(j, g, 0) for g in range(2) for j in range(2)}
    assert bar_meta == expected


# ── SVG inertness ──────────────────────────────────────────────────


def test_tagged_figure_svg_has_no_tag_bytes(tmp_path):
    """Tagging is inert: the tag attribute never leaks into rendered SVG output."""
    view = BarChartView(outdir=tmp_path)
    fig = view.create_figure(
        metadata={"title": "T"},
        device="desktop",
        categories=["A", "B", "C"],
        values=[3, 5, 2],
        show_values=True,
        legend=False,
    )
    # Sanity check: the figure is actually tagged.
    assert _tags(fig), "expected tagged artists in the figure"

    buf = BytesIO()
    fig.savefig(buf, format="svg")
    svg_bytes = buf.getvalue()

    assert b"_tps_anim" not in svg_bytes
    assert b"tps_anim" not in svg_bytes


# ── Import-order guard ─────────────────────────────────────────────


def test_importing_views_does_not_load_animation_stack():
    """Importing tpsplots.views must not eagerly import the animation/encoder stack.

    Guards the strict animation→views import direction: views tag via the
    stdlib-only anim_tags module and must never pull in matplotlib.animation or
    the ffmpeg wrapper at import time.
    """
    code = (
        "import sys, tpsplots.views; "
        "assert 'matplotlib.animation' not in sys.modules, 'matplotlib.animation leaked'; "
        "assert 'imageio_ffmpeg' not in sys.modules, 'imageio_ffmpeg leaked'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
