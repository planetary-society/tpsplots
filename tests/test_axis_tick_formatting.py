"""Tests for axis tick formatting across chart view types."""

from tpsplots.views.bar_chart import BarChartView
from tpsplots.views.grouped_bar_chart import GroupedBarChartView
from tpsplots.views.line_subplots import LineSubplotsView
from tpsplots.views.lollipop_chart import LollipopChartView
from tpsplots.views.stacked_bar_chart import StackedBarChartView


def _non_empty_tick_texts(ticks) -> list[str]:
    """Return rendered non-empty tick label text."""
    return [tick.get_text() for tick in ticks if tick.get_text()]


def test_bar_chart_applies_y_tick_format(tmp_path):
    """Bar chart should apply y-axis f-string tick formatting."""
    view = BarChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        values=[10000, 20000, 30000],
        y_tick_format=",.0f",
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = _non_empty_tick_texts(ax.get_yticklabels())
    assert any("," in label for label in y_labels)


def test_bar_chart_scale_composes_with_x_tick_format_for_horizontal(tmp_path):
    """Horizontal bar chart should compose scale and x-axis tick formatting."""
    view = BarChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        orientation="horizontal",
        categories=["A", "B", "C"],
        values=[10000, 20000, 30000],
        scale="thousands",
        x_tick_format=".2f",
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    x_labels = _non_empty_tick_texts(ax.get_xticklabels())
    assert any(label.endswith("K") for label in x_labels)
    assert any(".00K" in label for label in x_labels)


def test_stacked_bar_chart_scale_composes_with_y_tick_format(tmp_path):
    """Stacked bar chart should compose y-axis scale and tick formatting."""
    view = StackedBarChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        values={"Series A": [1000, 2000, 3000], "Series B": [1000, 1000, 1000]},
        scale="thousands",
        y_tick_format=".1f",
        legend=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = _non_empty_tick_texts(ax.get_yticklabels())
    assert any(label.endswith("K") for label in y_labels)
    assert any(".0K" in label for label in y_labels)


def test_grouped_bar_chart_applies_y_tick_format(tmp_path):
    """Grouped bar chart should apply y-axis f-string tick formatting."""
    view = GroupedBarChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "A", "values": [10000, 20000, 30000]},
            {"label": "B", "values": [12000, 22000, 32000]},
        ],
        show_yticks=True,
        y_tick_format=",.0f",
        legend=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = _non_empty_tick_texts(ax.get_yticklabels())
    assert any("," in label for label in y_labels)


def test_lollipop_chart_scale_composes_with_x_tick_format(tmp_path):
    """Lollipop chart should compose x-axis scale and tick formatting."""
    view = LollipopChartView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        start_values=[1000, 2000, 3000],
        end_values=[5000, 6000, 7000],
        scale="thousands",
        x_tick_format=".2f",
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    x_labels = _non_empty_tick_texts(ax.get_xticklabels())
    assert any(label.endswith("K") for label in x_labels)
    assert any(".00K" in label for label in x_labels)


def test_line_subplots_scale_composes_with_y_tick_format(tmp_path):
    """Line subplots should compose y-axis scale and tick formatting."""
    view = LineSubplotsView(outdir=tmp_path, style_file=None)

    fig = view._create_chart(
        metadata={"title": "Test"},
        style=view.DESKTOP,
        subplot_data=[
            {
                "x": [1, 2, 3],
                "y": [1000, 2000, 3000],
                "title": "One",
            }
        ],
        scale="thousands",
        axis_scale="y",
        y_tick_format=".1f",
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    fig.canvas.draw()
    y_labels = _non_empty_tick_texts(ax.get_yticklabels())
    assert any(label.endswith("K") for label in y_labels)
    assert any(".0K" in label for label in y_labels)
