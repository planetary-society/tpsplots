"""Targeted tests for simplified view helper paths."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
