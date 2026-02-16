"""Tests for scatter chart view behavior."""

import numpy as np
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


def test_scatter_create_figure_applies_scatter_defaults(tmp_path):
    """create_figure path should default to marker-only scatter styling."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)
    fig = view.create_figure(
        metadata={"title": "Test"},
        device="desktop",
        x=[1, 2, 3],
        y=[4, 5, 6],
        legend=False,
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    assert len(ax.get_lines()) == 1
    line = ax.get_lines()[0]
    assert line.get_linestyle() == "None"
    assert line.get_marker() == "o"


def test_scatter_create_chart_applies_y_tick_format(tmp_path):
    """Scatter chart should apply f-string style y-axis tick formatting."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        x=np.array([1, 2, 3]),
        y=np.array([5000, 15000, 25000]),
        y_tick_format=",.0f",
        legend=False,
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = [tick.get_text() for tick in ax.get_yticklabels() if tick.get_text()]
    assert any("," in label for label in y_labels)


def test_scatter_create_chart_applies_x_tick_format(tmp_path):
    """Scatter chart should apply f-string style x-axis tick formatting."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        x=np.array([1, 2, 3]),
        y=np.array([10, 20, 30]),
        x_tick_format=".1f",
        xticks=[1, 2, 3],
        legend=False,
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    x_labels = [tick.get_text() for tick in ax.get_xticklabels() if tick.get_text()]
    assert "1.0" in x_labels


def test_scatter_tick_format_works_with_scale_formatter(tmp_path):
    """Tick format specs should compose with scale formatting on the scaled axis."""
    view = ScatterChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        x=np.array([1, 2, 3]),
        y=np.array([1000, 2000, 3000]),
        scale="thousands",
        axis_scale="y",
        y_tick_format=".1f",
        legend=False,
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = [tick.get_text() for tick in ax.get_yticklabels() if tick.get_text()]
    assert any(label.endswith("K") for label in y_labels)
    assert any(".0K" in label for label in y_labels)
