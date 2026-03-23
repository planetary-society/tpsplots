"""Targeted tests for simplified view helper paths."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from tpsplots.views.line_chart import LineChartView
from tpsplots.views.line_subplots import LineSubplotsView
from tpsplots.views.us_map_pie_charts import USMapPieChartView


def test_direct_line_label_simple_position_uses_expected_alignment(tmp_path):
    """Simple endpoint label placement should honor right-position alignment."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [1, 2, 3], color="blue")
    fig.canvas.draw()

    text_bbox = view._get_text_bbox_display(
        "Series A",
        fontsize=12,
        color="blue",
        add_bbox=True,
        renderer=fig.canvas.get_renderer(),
        ax=ax,
    )
    pos = view._get_simple_label_position(
        x_data=2,
        y_data=3,
        text_bbox=text_bbox,
        position_mode="right",
        ax=ax,
        markersize_points=6,
    )

    assert pos["ha"] == "left"
    assert pos["va"] == "center"
    assert pos["x_data"] > 2


def test_direct_line_label_auto_places_labels_for_all_series(tmp_path):
    """Auto endpoint labeling should place one visible label per named series."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    x_data = [0, 1, 2, 3]
    y_data = [
        [1.0, 1.1, 1.2, 1.3],
        [1.05, 1.15, 1.25, 1.35],
    ]
    for series in y_data:
        ax.plot(x_data, series)
    fig.canvas.draw()

    view._add_direct_line_endpoint_labels(
        ax,
        x_data=x_data,
        y_data=y_data,
        labels=["One", "Two"],
        colors=["#037CC2", "#FF5D47"],
        style=view.DESKTOP,
        fig=fig,
        direct_line_labels={"position": "auto", "bbox": True},
        markersize=6,
    )

    text_values = [t.get_text() for t in ax.texts]
    assert "One" in text_values
    assert "Two" in text_values


def test_direct_line_label_text_bbox_uses_real_extent(tmp_path):
    """Temporary text measurement should return the rendered bbox, not a placeholder box."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    fig.canvas.draw()

    text_bbox = view._get_text_bbox_display(
        "Series A",
        fontsize=12,
        color="blue",
        add_bbox=True,
        renderer=fig.canvas.get_renderer(),
        ax=ax,
    )

    assert text_bbox is not None
    assert text_bbox.width > 10
    assert text_bbox.height > 10


def test_direct_line_label_auto_datetime_axis_avoids_runtime_warnings(tmp_path):
    """Auto endpoint labels should handle datetime x-values without transform warnings."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig, ax = plt.subplots()
    x_data = pd.to_datetime(["2024-01-01", "2025-01-01", "2026-01-01"])
    y_data = [
        [1.0, 1.1, 1.2],
        [1.05, 1.15, 1.25],
    ]
    for series in y_data:
        ax.plot(x_data, series)
    fig.canvas.draw()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        view._add_direct_line_endpoint_labels(
            ax,
            x_data=x_data,
            y_data=y_data,
            labels=["One", "Two"],
            colors=["#037CC2", "#FF5D47"],
            style=view.DESKTOP,
            fig=fig,
            direct_line_labels={"position": "auto", "bbox": True},
            markersize=6,
        )

    runtime_warnings = [
        warning for warning in caught if issubclass(warning.category, RuntimeWarning)
    ]
    assert runtime_warnings == []
    assert all(abs(text.get_position()[0]) < 1e6 for text in ax.texts)


def test_line_chart_grid_dict_still_applies_custom_axis(tmp_path):
    """Line chart should still honor dict-style grid arguments."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grid Dict"},
        style=view.DESKTOP,
        x=[1, 2, 3, 4],
        y=[[10, 20, 30, 40]],
        legend=False,
        fiscal_year_ticks=False,
        grid={"axis": "x", "alpha": 0.25},
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert any(line.get_visible() for line in ax.get_xgridlines())
    assert not any(line.get_visible() for line in ax.get_ygridlines())


def test_line_chart_axis_labels_are_italic_with_grid_dict(tmp_path):
    """Line chart axis labels should remain italic in the dict-grid branch."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Italic Labels"},
        style=view.DESKTOP,
        x=[1, 2, 3, 4],
        y=[[10, 20, 30, 40]],
        xlabel="Year",
        ylabel="Amount",
        legend=False,
        fiscal_year_ticks=False,
        grid={"axis": "x", "alpha": 0.25},
    )
    ax = fig.axes[0]

    assert ax.xaxis.label.get_fontstyle() == "italic"
    assert ax.yaxis.label.get_fontstyle() == "italic"


def test_line_chart_grid_axis_kwarg_controls_visible_axis(tmp_path):
    """Line chart should honor explicit grid_axis when grid is enabled."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grid Axis"},
        style=view.DESKTOP,
        x=[1, 2, 3, 4],
        y=[[10, 20, 30, 40]],
        legend=False,
        fiscal_year_ticks=False,
        grid=True,
        grid_axis="x",
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert any(line.get_visible() for line in ax.get_xgridlines())
    assert not any(line.get_visible() for line in ax.get_ygridlines())


def test_grouped_bar_keeps_y_grid_when_y_tick_labels_hidden(tmp_path):
    """Grouped bar chart should preserve y-gridlines when hiding y-axis labels."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Grid"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        grid=True,
        grid_axis="y",
        show_yticks=False,
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert any(line.get_visible() for line in ax.get_ygridlines())
    assert not any(tick.get_text() for tick in ax.get_yticklabels())


def test_grouped_bar_shows_y_axis_by_default(tmp_path):
    """Grouped bar chart should show the y-axis by default."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Default Axis"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert any(tick.get_text() for tick in ax.get_yticklabels())


def test_grouped_bar_defaults_match_bar_family_contract(tmp_path):
    """Grouped bar should use the shared default grid/legend/show-values contract."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Defaults"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert any(line.get_visible() for line in ax.get_ygridlines())
    assert ax.get_legend() is not None
    assert ax.get_legend()._loc == 0
    assert not ax.texts


def test_grouped_bar_y_axis_matches_default_chart_style(tmp_path):
    """Grouped bar chart should render the default shared y-axis visual style."""
    import matplotlib.pyplot as plt

    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    grouped_view = GroupedBarChartView(outdir=tmp_path, style_file=None)

    grouped_fig = grouped_view._create_chart(
        metadata={"title": "Grouped"},
        style=grouped_view.DESKTOP,
        categories=["A", "B"],
        groups=[
            {"label": "First", "values": [10, 20]},
            {"label": "Second", "values": [12, 22]},
        ],
        xlabel="Category",
        ylabel="Value",
        legend=False,
    )

    grouped_ax = grouped_fig.axes[0]
    grouped_fig.canvas.draw()

    grouped_tick = grouped_ax.yaxis.get_major_ticks()[0]
    expected_label_color = plt.rcParams["ytick.labelcolor"]
    if expected_label_color == "inherit":
        expected_label_color = plt.rcParams["axes.labelcolor"]

    assert grouped_ax.spines["left"].get_visible() == plt.rcParams["axes.spines.left"]
    if grouped_ax.spines["left"].get_visible():
        assert grouped_ax.spines["left"].get_linewidth() == plt.rcParams["axes.linewidth"]
        assert grouped_ax.spines["left"].get_edgecolor() == plt.matplotlib.colors.to_rgba(
            plt.rcParams["axes.edgecolor"]
        )
    assert grouped_ax.yaxis.label.get_fontstyle() == "italic"
    assert grouped_ax.get_yticklabels()[0].get_fontsize() == grouped_view.DESKTOP["tick_size"]
    assert grouped_tick.tick1line.get_visible()
    assert grouped_tick.tick1line.get_markersize() == plt.rcParams["ytick.major.size"]
    assert grouped_tick.tick1line.get_markeredgewidth() == plt.rcParams["ytick.major.width"]
    assert grouped_tick.tick1line.get_color() == plt.rcParams["ytick.color"]
    assert grouped_ax.get_yticklabels()[0].get_color() == expected_label_color


def test_bar_family_value_axis_matches_default_styling(tmp_path):
    """Bar-family charts should inherit the default matplotlib value-axis styling."""
    from tpsplots.views.bar_chart import BarChartView
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    chart_cases = [
        (
            BarChartView,
            {
                "categories": ["A", "B"],
                "values": [10, 20],
                "legend": False,
            },
        ),
        (
            GroupedBarChartView,
            {
                "categories": ["A", "B"],
                "groups": [
                    {"label": "First", "values": [10, 20]},
                    {"label": "Second", "values": [12, 22]},
                ],
                "legend": False,
            },
        ),
        (
            StackedBarChartView,
            {
                "categories": ["A", "B"],
                "values": {"One": [10, 20], "Two": [5, 15]},
                "legend": False,
            },
        ),
    ]

    with plt.rc_context(
        {
            "axes.spines.left": False,
            "axes.linewidth": 2.0,
            "axes.edgecolor": "#414141",
            "ytick.major.width": 1.3,
            "ytick.major.size": 6.0,
            "ytick.color": "#414141",
            "ytick.labelcolor": "#414141",
        }
    ):
        ref_fig, ref_ax = plt.subplots()
        ref_ax.plot([0, 1], [0, 1])
        ref_ax.set_ylabel("Value")
        ref_fig.canvas.draw()

        ref_tick = ref_ax.yaxis.get_major_ticks()[0]
        for view_cls, kwargs in chart_cases:
            view = view_cls(outdir=tmp_path, style_file=None)
            fig = view._create_chart(
                metadata={"title": "Axis RC"},
                style=view.DESKTOP,
                **kwargs,
            )
            ax = fig.axes[0]
            fig.canvas.draw()
            tick = ax.yaxis.get_major_ticks()[0]

            assert ax.spines["left"].get_visible() == ref_ax.spines["left"].get_visible()
            assert ax.spines["left"].get_linewidth() == ref_ax.spines["left"].get_linewidth()
            assert ax.spines["left"].get_edgecolor() == ref_ax.spines["left"].get_edgecolor()
            assert tick.tick1line.get_visible() == ref_tick.tick1line.get_visible()
            assert tick.tick1line.get_markersize() == ref_tick.tick1line.get_markersize()
            assert tick.tick1line.get_markeredgewidth() == ref_tick.tick1line.get_markeredgewidth()
            assert tick.tick1line.get_color() == ref_tick.tick1line.get_color()
            assert ax.get_yticklabels()[0].get_color() == ref_ax.get_yticklabels()[0].get_color()


def test_grouped_bar_hides_category_tick_marks_by_default(tmp_path):
    """Grouped bar chart should hide x-axis category tick marks by default."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Tick Marks"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert not ax.xaxis.get_major_ticks()[0].tick1line.get_visible()


def test_grouped_bar_respects_label_size_override(tmp_path):
    """Grouped bar chart should honor explicit axis label size overrides."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Labels"},
        style=view.DESKTOP,
        categories=["A", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        xlabel="Category",
        ylabel="Value",
        label_size=31,
        legend=False,
    )
    ax = fig.axes[0]

    assert ax.xaxis.label.get_size() == 31
    assert ax.yaxis.label.get_size() == 31


@pytest.mark.parametrize(
    ("view_cls", "chart_kwargs"),
    [
        (
            "bar",
            {
                "categories": [
                    "Category label that is intentionally very long 1",
                    "Category label that is intentionally very long 2",
                    "Category label that is intentionally very long 3",
                ],
                "values": [10, 20, 30],
            },
        ),
        (
            "grouped_bar",
            {
                "categories": [
                    "Category label that is intentionally very long 1",
                    "Category label that is intentionally very long 2",
                    "Category label that is intentionally very long 3",
                ],
                "groups": [
                    {"label": "First", "values": [10, 20, 30]},
                    {"label": "Second", "values": [12, 22, 32]},
                ],
                "legend": False,
            },
        ),
        (
            "stacked_bar",
            {
                "categories": [
                    "Category label that is intentionally very long 1",
                    "Category label that is intentionally very long 2",
                    "Category label that is intentionally very long 3",
                ],
                "values": {"One": [10, 20, 30], "Two": [5, 15, 25]},
                "legend": False,
            },
        ),
    ],
)
def test_bar_family_auto_rotates_long_category_labels(tmp_path, view_cls, chart_kwargs):
    """Bar-family charts should share the long-label auto-rotation heuristic."""
    from tpsplots.views.bar_chart import BarChartView
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    views = {
        "bar": BarChartView,
        "grouped_bar": GroupedBarChartView,
        "stacked_bar": StackedBarChartView,
    }
    view = views[view_cls](outdir=tmp_path, style_file=None)
    style = {**view.DESKTOP, "figsize": (4, 4)}
    fig = view._create_chart(
        metadata={"title": "Auto Rotation"},
        style=style,
        **chart_kwargs,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_xticklabels()[0].get_rotation() == 90


@pytest.mark.parametrize(
    ("view_cls", "chart_kwargs"),
    [
        (
            "bar",
            {
                "categories": ["A", "B"],
                "values": [10, 20],
                "show_yticks": False,
                "legend": False,
            },
        ),
        (
            "grouped_bar",
            {
                "categories": ["A", "B"],
                "groups": [
                    {"label": "First", "values": [10, 20]},
                    {"label": "Second", "values": [12, 22]},
                ],
                "show_yticks": False,
                "legend": False,
            },
        ),
        (
            "stacked_bar",
            {
                "categories": ["A", "B"],
                "values": {"One": [10, 20], "Two": [5, 15]},
                "show_yticks": False,
                "legend": False,
            },
        ),
    ],
)
def test_bar_family_hides_vertical_value_axis_when_show_yticks_false(
    tmp_path, view_cls, chart_kwargs
):
    """Vertical bar-family charts should hide the y value axis consistently."""
    from tpsplots.views.bar_chart import BarChartView
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    views = {
        "bar": BarChartView,
        "grouped_bar": GroupedBarChartView,
        "stacked_bar": StackedBarChartView,
    }
    view = views[view_cls](outdir=tmp_path, style_file=None)
    fig = view._create_chart(metadata={"title": "Hide Y"}, style=view.DESKTOP, **chart_kwargs)
    ax = fig.axes[0]
    fig.canvas.draw()

    assert not any(tick.get_text() for tick in ax.get_yticklabels())
    assert not ax.spines["left"].get_visible()


@pytest.mark.parametrize(
    ("view_cls", "chart_kwargs"),
    [
        (
            "bar",
            {
                "categories": ["A", "B"],
                "values": [10, 20],
                "orientation": "horizontal",
                "show_xticks": False,
                "legend": False,
            },
        ),
        (
            "stacked_bar",
            {
                "categories": ["A", "B"],
                "values": {"One": [10, 20], "Two": [5, 15]},
                "orientation": "horizontal",
                "show_xticks": False,
                "legend": False,
            },
        ),
    ],
)
def test_bar_family_hides_horizontal_value_axis_when_show_xticks_false(
    tmp_path, view_cls, chart_kwargs
):
    """Horizontal bar-family charts should hide the x value axis consistently."""
    from tpsplots.views.bar_chart import BarChartView
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    views = {
        "bar": BarChartView,
        "stacked_bar": StackedBarChartView,
    }
    view = views[view_cls](outdir=tmp_path, style_file=None)
    fig = view._create_chart(metadata={"title": "Hide X"}, style=view.DESKTOP, **chart_kwargs)
    ax = fig.axes[0]
    fig.canvas.draw()

    assert not any(tick.get_text() for tick in ax.get_xticklabels())
    assert not ax.spines["bottom"].get_visible()


@pytest.mark.parametrize(
    ("view_cls", "chart_kwargs", "message"),
    [
        (
            "bar",
            {"categories": ["A"], "values": [1], "orientation": "vertical", "show_xticks": False},
            "show_xticks is only supported for horizontal bar charts",
        ),
        (
            "bar",
            {"categories": ["A"], "values": [1], "orientation": "horizontal", "show_yticks": False},
            "show_yticks is only supported for vertical bar charts",
        ),
        (
            "stacked_bar",
            {
                "categories": ["A"],
                "values": {"One": [1]},
                "orientation": "vertical",
                "show_xticks": False,
            },
            "show_xticks is only supported for horizontal bar charts",
        ),
        (
            "stacked_bar",
            {
                "categories": ["A"],
                "values": {"One": [1]},
                "orientation": "horizontal",
                "show_yticks": False,
            },
            "show_yticks is only supported for vertical bar charts",
        ),
        (
            "grouped_bar",
            {
                "categories": ["A"],
                "groups": [{"label": "First", "values": [1]}],
                "show_xticks": False,
            },
            "show_xticks is only supported for horizontal bar charts",
        ),
    ],
)
def test_bar_family_rejects_incompatible_value_axis_tick_options(
    tmp_path, view_cls, chart_kwargs, message
):
    """Bar-family charts should reject x/y value-axis tick options on the wrong orientation."""
    from tpsplots.views.bar_chart import BarChartView
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    views = {
        "bar": BarChartView,
        "grouped_bar": GroupedBarChartView,
        "stacked_bar": StackedBarChartView,
    }
    view = views[view_cls](outdir=tmp_path, style_file=None)

    with pytest.raises(ValueError, match=message):
        view._create_chart(
            metadata={"title": "Invalid Axis Ticks"}, style=view.DESKTOP, **chart_kwargs
        )


def test_stacked_bar_default_legend_uses_auto_location(tmp_path):
    """Stacked bars should default to an auto-placed legend when enabled."""
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    view = StackedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Stacked Legend"},
        style=view.DESKTOP,
        categories=["A", "B"],
        values={"One": [10, 20], "Two": [5, 15]},
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_legend() is not None
    assert ax.get_legend()._loc == 0


def test_bar_value_based_legend_uses_auto_location_when_enabled(tmp_path):
    """Regular bars should use auto legend placement when value-based legend is enabled."""
    from tpsplots.views.bar_chart import BarChartView

    view = BarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Bar Legend"},
        style=view.DESKTOP,
        categories=["A", "B"],
        values=[10, -5],
        positive_color="green",
        negative_color="red",
        legend=True,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_legend() is not None
    assert ax.get_legend()._loc == 0


def test_grouped_bar_parses_literal_newlines_in_category_labels(tmp_path):
    """Grouped bar chart should convert literal \\n sequences into real line breaks."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Newlines"},
        style=view.DESKTOP,
        categories=["Line 1\\nLine 2", "B", "C"],
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_xticklabels()[0].get_text() == "Line 1\nLine 2"


def test_bar_formats_datetime_categories_as_years_by_default(tmp_path):
    """Bar charts should auto-render datetime categories as readable years."""
    from tpsplots.views.bar_chart import BarChartView

    view = BarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Bar Years"},
        style=view.DESKTOP,
        categories=pd.to_datetime(["1959-01-01", "1960-01-01", "1961-01-01"]),
        values=[1, 2, 3],
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_xticklabels()[0].get_text() == "1959"
    assert ax.get_xticklabels()[1].get_text() == "1960"


def test_grouped_bar_formats_datetime_categories_as_years_by_default(tmp_path):
    """Grouped bars should auto-render datetime categories as readable years."""
    from tpsplots.views.grouped_bar_chart import GroupedBarChartView

    view = GroupedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Grouped Years"},
        style=view.DESKTOP,
        categories=pd.to_datetime(["1959-01-01", "1960-01-01", "1961-01-01"]),
        groups=[
            {"label": "First", "values": [10, 20, 30]},
            {"label": "Second", "values": [12, 22, 32]},
        ],
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_xticklabels()[0].get_text() == "1959"
    assert ax.get_xticklabels()[1].get_text() == "1960"


def test_stacked_bar_formats_datetime_categories_with_explicit_label_format(tmp_path):
    """Stacked bars should support explicit categorical date label formatting."""
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    view = StackedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Stacked Years"},
        style=view.DESKTOP,
        categories=pd.to_datetime(["1959-01-01", "1960-01-01"]),
        values={"One": [10, 20], "Two": [5, 15]},
        category_label_format="%Y",
        legend=False,
    )
    ax = fig.axes[0]
    fig.canvas.draw()

    assert ax.get_xticklabels()[0].get_text() == "1959"
    assert ax.get_xticklabels()[1].get_text() == "1960"


def test_stacked_bar_axis_labels_are_italic(tmp_path):
    """Stacked bar chart axis labels should render in italics."""
    from tpsplots.views.stacked_bar_chart import StackedBarChartView

    view = StackedBarChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Italic Stack"},
        style=view.DESKTOP,
        categories=["A", "B"],
        values={"One": [10, 20], "Two": [5, 15]},
        xlabel="Category",
        ylabel="Value",
        legend=False,
    )
    ax = fig.axes[0]

    assert ax.xaxis.label.get_fontstyle() == "italic"
    assert ax.yaxis.label.get_fontstyle() == "italic"


def test_line_chart_direct_labels_do_not_duplicate_markersize_kwarg(tmp_path):
    """Direct labels should render without passing markersize twice."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Direct Labels"},
        style=view.DESKTOP,
        x=[1, 2, 3],
        y=[[2, 3, 4]],
        labels=["Series A"],
        direct_line_labels={"position": "right", "bbox": True},
        legend=False,
        fiscal_year_ticks=False,
    )

    texts = [t.get_text() for t in fig.axes[0].texts]
    assert "Series A" in texts


def test_line_chart_supports_per_series_markersize_and_direct_labels(tmp_path):
    """Line charts should accept per-series markersize arrays end-to-end."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Per-Series Marker Size"},
        style=view.DESKTOP,
        x=[1, 2, 3],
        y=[[2, 3, 4], [3, 4, 5]],
        labels=["Series A", "Series B"],
        markersize=[4, 10],
        direct_line_labels={"position": "right", "bbox": True},
        legend=False,
        fiscal_year_ticks=False,
    )

    lines = fig.axes[0].get_lines()
    assert len(lines) >= 2
    assert lines[0].get_markersize() == 4
    assert lines[1].get_markersize() == 10
    texts = [t.get_text() for t in fig.axes[0].texts]
    assert "Series A" in texts
    assert "Series B" in texts


def test_generate_chart_preserves_xlim_for_stringified_numeric_x_data(tmp_path):
    """Stringified numeric x-data should not let social tick thinning override xlim."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    data = pd.DataFrame(
        {
            "Years from Start": [str(i) for i in range(23)] + ["Totals"],
            "Apollo (2025 $)": [float(i) for i in range(14)] + [None] * 10,
            "STS (2025 $)": [float(i) * 2 for i in range(11)] + [None] * 13,
        }
    )

    def _skip_save(fig, filename, metadata, create_pptx=False, create_svg=True):
        return []

    view._save_chart = _skip_save  # type: ignore[method-assign]

    result = view.generate_chart(
        metadata={"title": "Numeric XLim"},
        stem="numeric_xlim",
        data=data,
        x="Years from Start",
        y=["Apollo (2025 $)", "STS (2025 $)"],
        xlim=[0, 14],
        fiscal_year_ticks=False,
        scale="billions",
        legend=False,
    )

    for device in ("desktop", "mobile", "social"):
        ax = result[device].axes[0]
        assert tuple(ax.get_xlim()) == (0.0, 14.0)

    social_ticks = result["social"].axes[0].get_xticks()
    assert max(social_ticks) <= 14.0


def test_line_subplots_shared_legend_and_shared_axes(tmp_path):
    """Shared legend mode should produce one figure-level legend and shared axes."""
    view = LineSubplotsView(outdir=tmp_path, style_file=None)
    fig = view._create_chart(
        metadata={"title": "Shared Legend"},
        style=view.DESKTOP,
        subplot_data=[
            {"x": [1, 2, 3], "y": [[1, 2, 3], [2, 3, 4]], "labels": ["A", "B"], "title": "Top"},
            {"x": [1, 2, 3], "y": [[3, 2, 1], [4, 3, 2]], "labels": ["A", "B"], "title": "Bottom"},
        ],
        grid_shape=(2, 1),
        shared_x=True,
        shared_y=True,
        shared_legend=True,
        legend=True,
        fiscal_year_ticks=False,
    )

    assert len(fig.legends) == 1
    legend_text = [t.get_text() for t in fig.legends[0].get_texts()]
    assert legend_text == ["A", "B"]

    ax0, ax1 = fig.axes[:2]
    assert ax0.get_shared_x_axes().joined(ax0, ax1)
    assert ax0.get_shared_y_axes().joined(ax0, ax1)


def test_line_chart_resolve_line_data_supports_extension_array(tmp_path):
    """ExtensionArray x input should still coerce to single-series y data."""
    view = LineChartView(outdir=tmp_path, style_file=None)
    kwargs = {"x": pd.array([1, 2, 3], dtype="Int64")}

    x_data, y_data, _data_ref = view._resolve_line_data(kwargs)

    assert list(x_data) == [0, 1, 2]
    assert y_data is not None
    assert len(y_data) == 1
    assert list(y_data[0]) == [1, 2, 3]


def test_us_map_consistent_radius_preserves_legacy_offset_scale(tmp_path):
    """Offset radius helper should retain the legacy conversion scale."""
    view = USMapPieChartView(outdir=tmp_path, style_file=None)

    scatter_size = 800
    expected = np.sqrt(scatter_size) / 72.0 * 8.0 * 0.8
    radius = view._calculate_consistent_pie_radius(scatter_size)
    assert radius == expected


def test_us_map_helpers_fallback_to_base_size_when_pie_size_missing(tmp_path):
    """Helpers should keep rendering when a location is missing from pie_sizes."""
    view = USMapPieChartView(outdir=tmp_path, style_file=None)
    base_pie_size = 900

    _fig, ax = plt.subplots()
    captured_sizes = []

    def fake_draw(values, xpos, ypos, size, colors, axis, show_percentages, figsize, dpi, style):
        captured_sizes.append(size)
        return axis

    view._draw_pie_improved = fake_draw  # type: ignore[method-assign]

    pie_data = {
        "JSC": {"values": [1], "labels": ["A"], "colors": ["#037CC2"]},
    }
    all_locations = {**view.NASA_CENTERS}
    pie_sizes: dict[str, float] = {}

    positions = view._collect_pie_positions_and_sizes(
        pie_data,
        all_locations,
        offset_positions={},
        pie_sizes=pie_sizes,
        base_pie_size=base_pie_size,
    )
    assert positions[0][2] == base_pie_size

    _legend_elements, _legend_labels = view._draw_pies_and_collect_legend(
        ax,
        pie_data,
        all_locations,
        offset_positions={},
        pie_sizes=pie_sizes,
        show_pie_labels=False,
        show_percentages=False,
        offset_line_color="gray",
        offset_line_style="--",
        offset_line_width=1.5,
        figsize=view.DESKTOP["figsize"],
        dpi=view.DESKTOP["dpi"],
        style=view.DESKTOP,
        base_pie_size=base_pie_size,
    )
    assert captured_sizes == [base_pie_size]


def test_us_map_offsets_generated_for_key_centers(tmp_path):
    """US map offset helper should continue resolving known overlapping centers."""
    view = USMapPieChartView(outdir=tmp_path, style_file=None)
    _fig, ax = plt.subplots()
    pie_data = {"JSC": {"values": [1]}, "ARC": {"values": [1]}, "SSC": {"values": [1]}}
    all_locations = {**view.NASA_CENTERS}
    pie_sizes = {name: 800 for name in pie_data}
    offsets = view._calculate_offset_positions(pie_data, all_locations, ax, pie_sizes, 800)

    for center in ("JSC", "ARC", "SSC"):
        assert center in offsets
