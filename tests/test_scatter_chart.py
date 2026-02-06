"""Tests for scatter chart view behavior."""

import pandas as pd

from tpsplots.views.scatter_chart import ScatterChartView


def test_scatter_plot_sets_scatter_defaults(tmp_path, monkeypatch):
    """Scatter plots should default to markers with no connecting lines."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)
    captured = {}

    def fake_generate_chart(metadata, stem, **kwargs):
        captured.update(kwargs)
        return {"desktop": object(), "mobile": object(), "files": []}

    monkeypatch.setattr(view, "generate_chart", fake_generate_chart)

    view.scatter_plot(metadata={"title": "Test"}, stem="scatter", x=[1, 2], y=[3, 4])

    assert captured["marker"] == "o"
    assert captured["linestyle"] == "None"


def test_scatter_plot_preserves_explicit_style_overrides(tmp_path, monkeypatch):
    """Explicit linestyle/marker options should not be overwritten."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)
    captured = {}

    def fake_generate_chart(metadata, stem, **kwargs):
        captured.update(kwargs)
        return {"desktop": object(), "mobile": object(), "files": []}

    monkeypatch.setattr(view, "generate_chart", fake_generate_chart)

    view.scatter_plot(
        metadata={"title": "Test"},
        stem="scatter",
        x=[1, 2],
        y=[3, 4],
        marker="x",
        linestyle="--",
    )

    assert captured["marker"] == "x"
    assert captured["linestyle"] == "--"


def test_scatter_create_chart_handles_nullable_int64_arrays(tmp_path):
    """Scatter chart should treat pandas Int64 arrays as a single data series."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)

    x = pd.array([2018, 2019, 2020], dtype="Int64")
    y = pd.array([1000, 1200, 1300], dtype="Int64")

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        x=x,
        y=y,
        legend=False,
    )

    ax = fig.axes[0]
    assert len(ax.get_lines()) == 1
    assert len(ax.get_lines()[0].get_xdata()) == 3
    assert len(ax.get_lines()[0].get_ydata()) == 3
