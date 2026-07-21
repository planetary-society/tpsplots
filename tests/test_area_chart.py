"""Tests for ordinary and stacked area chart behavior."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import yaml
from matplotlib.colors import to_rgba
from matplotlib.ticker import FuncFormatter
from pydantic import ValidationError

from tpsplots.models import AreaChartConfig
from tpsplots.models.chart_config import CHART_TYPES
from tpsplots.models.charts import CONFIG_REGISTRY
from tpsplots.views import VIEW_REGISTRY, AreaChartView
from tpsplots.views.anim_tags import Roles, get_tag


def _view(tmp_path) -> AreaChartView:
    return AreaChartView(outdir=tmp_path, style_file=None)


def test_area_public_registries_and_config_export():
    assert CHART_TYPES["area"] == "area_plot"
    assert CONFIG_REGISTRY["area"] is AreaChartConfig
    assert VIEW_REGISTRY["area_plot"] is AreaChartView
    assert AreaChartView.CONFIG_CLASS is AreaChartConfig


def test_area_has_scaffold_docs_example_and_local_stacked_example():
    from tpsplots.docs_generator import MINIMAL_EXAMPLES
    from tpsplots.templates import TEMPLATES

    assert "type: area" in TEMPLATES["area"]
    assert "stacked: true" in TEMPLATES["area"]
    assert "type: area" in MINIMAL_EXAMPLES["area"]
    example = Path(__file__).parent.parent / "yaml" / "examples" / "area_budget_composition.yaml"
    assert example.exists()
    example_config = yaml.safe_load(example.read_text(encoding="utf-8"))
    assert example_config["chart"]["stacked"] is True
    assert example_config["chart"]["legend"] == {
        "loc": "upper center",
        "bbox_to_anchor": [0.5, -0.12],
        "ncol": 3,
        "fontsize": 9,
        "frameon": False,
        "columnspacing": 1.0,
        "handletextpad": 0.4,
    }


def test_area_config_exposes_area_fields_but_not_line_only_fields():
    fields = set(AreaChartConfig.model_fields)
    assert {
        "x",
        "y",
        "data",
        "stacked",
        "color",
        "labels",
        "alpha",
        "edgecolor",
        "linewidth",
        "linestyle",
        "xticks",
        "xticklabels",
    } <= fields
    assert {"y_right", "marker", "direct_line_labels", "series_types", "hlines"}.isdisjoint(fields)


@pytest.mark.parametrize("key", ["x", "y", "baseline", "where", "y1", "y2"])
def test_area_config_rejects_geometry_in_matplotlib_escape_hatch(key):
    with pytest.raises(ValidationError, match="geometry"):
        AreaChartConfig(
            output="area",
            title="Area",
            x=[1, 2],
            y=[1, 2],
            matplotlib_config={key: 1},
        )


def test_ordinary_area_creates_one_tagged_collection_per_series(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2, 3],
        y=[[1, 2, 3], [3, 2, 1]],
        labels=["A", "B"],
        color=["#ff0000", "#0000ff"],
        legend=True,
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    assert len(ax.collections) == 2
    assert [get_tag(c).role for c in ax.collections] == [Roles.SERIES, Roles.SERIES]
    assert [get_tag(c).index for c in ax.collections] == [0, 1]
    assert [c.get_label() for c in ax.collections] == ["A", "B"]
    assert [c.get_alpha() for c in ax.collections] == [0.65, 0.65]
    assert ax.get_ylim()[0] == pytest.approx(0)


def test_stacked_area_uses_bottom_to_top_input_order(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2, 3],
        y=[[1, 2, 3], [4, 5, 6]],
        stacked=True,
        labels=["Bottom", "Top"],
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    assert len(ax.collections) == 2
    assert [c.get_label() for c in ax.collections] == ["Bottom", "Top"]
    assert [c.get_alpha() for c in ax.collections] == [1.0, 1.0]
    assert ax.dataLim.y0 == pytest.approx(0)
    assert ax.dataLim.y1 == pytest.approx(9)


def test_default_color_cycle_is_identical_for_ordinary_and_stacked_areas(tmp_path):
    kwargs = {
        "metadata": {"title": "T"},
        "style": AreaChartView.DESKTOP,
        "x": [1, 2, 3],
        "y": [[1, 2, 3], [3, 2, 1]],
        "fiscal_year_ticks": False,
    }
    ordinary = _view(tmp_path)._create_chart(**kwargs)
    stacked = _view(tmp_path)._create_chart(**kwargs, stacked=True)

    ordinary_colors = [
        collection.get_facecolor()[0, :3] for collection in ordinary.axes[0].collections
    ]
    stacked_colors = [
        collection.get_facecolor()[0, :3] for collection in stacked.axes[0].collections
    ]
    expected = [
        to_rgba(color)[:3] for color in plt.rcParams["axes.prop_cycle"].by_key()["color"][:2]
    ]
    assert np.allclose(ordinary_colors, expected)
    assert np.allclose(stacked_colors, expected)


def test_area_resolves_dataframe_columns_and_reverses_descending_x(tmp_path):
    data = pd.DataFrame({"Year": [2023, 2022, 2021], "A": [3, 2, 1]})
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        data=data,
        x="Year",
        y="A",
        fiscal_year_ticks=False,
    )

    vertices = fig.axes[0].collections[0].get_paths()[0].vertices
    assert vertices[:, 0].min() == pytest.approx(2021)
    assert vertices[:, 0].max() == pytest.approx(2023)


def test_area_rejects_unsorted_continuous_x(tmp_path):
    with pytest.raises(ValueError, match="monotonic"):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=[1, 3, 2],
            y=[1, 2, 3],
            fiscal_year_ticks=False,
        )


@pytest.mark.parametrize(
    ("x", "y", "message"),
    [
        ([], [], "non-empty"),
        ([1, 2], [1], "same length"),
        ([1, np.inf], [1, 2], "infinite"),
        ([1, 2], [1, np.inf], "infinite"),
        ([1, 2], [1, "bad"], "non-numeric"),
    ],
)
def test_area_rejects_invalid_data_before_rendering(tmp_path, x, y, message):
    with pytest.raises(ValueError, match=message):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=x,
            y=y,
            fiscal_year_ticks=False,
        )


def test_stacked_area_rejects_negative_values(tmp_path):
    with pytest.raises(ValueError, match="negative"):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=[1, 2, 3],
            y=[[1, -1, 2], [2, 3, 4]],
            stacked=True,
            fiscal_year_ticks=False,
        )


def test_stacked_area_applies_common_nan_gap(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2, 3, 4, 5],
        y=[[1, 1, 1, 1, 1], [2, 2, np.nan, 2, 2]],
        stacked=True,
        fiscal_year_ticks=False,
    )

    collections = fig.axes[0].collections
    assert len(collections) == 2
    assert all(len(collection.get_paths()) == 2 for collection in collections)


def test_ordinary_area_preserves_independent_nan_gaps(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2, 3, 4, 5],
        y=[[1, 1, 1, 1, 1], [2, 2, np.nan, 2, 2]],
        fiscal_year_ticks=False,
    )

    first, second = fig.axes[0].collections
    assert len(first.get_paths()) == 1
    assert len(second.get_paths()) == 2


def test_area_uses_implicit_indices_for_y_only_input(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[3, 5, 4],
        fiscal_year_ticks=False,
    )

    vertices = fig.axes[0].collections[0].get_paths()[0].vertices
    assert vertices[:, 0].min() == pytest.approx(0)
    assert vertices[:, 0].max() == pytest.approx(2)


def test_area_preserves_categorical_order(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=["Beta", "Alpha", "Gamma"],
        y=[2, 1, 3],
        fiscal_year_ticks=False,
    )

    assert [tick.get_text() for tick in fig.axes[0].get_xticklabels()][:3] == [
        "Beta",
        "Alpha",
        "Gamma",
    ]


def test_area_sparse_styles_use_mode_defaults_and_scalar_label_is_first_only(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2],
        y=[[1, 2], [2, 3]],
        labels="Only",
        alpha=[None, 0.25],
        edgecolor=["#ff0000", None],
        linewidth=[1.5, None],
        linestyle=["--", None],
        fiscal_year_ticks=False,
    )

    first, second = fig.axes[0].collections
    assert [first.get_label(), second.get_label()] == ["Only", None]
    assert [first.get_alpha(), second.get_alpha()] == [0.65, 0.25]
    assert first.get_linewidths()[0] == pytest.approx(1.5)
    assert second.get_linewidths()[0] == pytest.approx(0)
    assert np.allclose(first.get_edgecolor()[0, :3], [1, 0, 0])
    assert second.get_edgecolor().size == 0


def test_area_escape_hatch_facecolor_wins_over_typed_color(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2],
        y=[1, 2],
        color="#ff0000",
        facecolor="#0000ff",
        fiscal_year_ticks=False,
    )

    assert np.allclose(fig.axes[0].collections[0].get_facecolor()[0, :3], [0, 0, 1])


def test_area_plural_collection_aliases_win_over_typed_styles(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2],
        y=[[1, 2], [2, 3]],
        color="#ff0000",
        edgecolor="none",
        linewidth=0,
        facecolors=["#0000ff", "#00ff00"],
        edgecolors=["#111111", "#222222"],
        linewidths=[1, 2],
        fiscal_year_ticks=False,
    )

    first, second = fig.axes[0].collections
    assert np.allclose(first.get_facecolor()[0, :3], [0, 0, 1])
    assert np.allclose(second.get_facecolor()[0, :3], [0, 1, 0])
    assert first.get_linewidths()[0] == pytest.approx(1)
    assert second.get_linewidths()[0] == pytest.approx(2)


def test_area_short_collection_aliases_and_label_win_over_typed_styles(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2],
        y=[1, 2],
        labels="Typed",
        color="#ff0000",
        edgecolor="none",
        linewidth=0,
        linestyle="-",
        fc="#0000ff",
        ec="#00ff00",
        lw=2,
        ls="--",
        label="Escape",
        fiscal_year_ticks=False,
    )

    collection = fig.axes[0].collections[0]
    assert np.allclose(collection.get_facecolor()[0, :3], [0, 0, 1])
    assert np.allclose(collection.get_edgecolor()[0, :3], [0, 1, 0])
    assert collection.get_linewidths()[0] == pytest.approx(2)
    assert collection.get_label() == "Escape"


def test_area_clips_before_autoscaling_y(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[1, 2, 3],
        y=[1, 2, 1_000_000],
        xlim=[1, 2],
        fiscal_year_ticks=False,
    )

    assert fig.axes[0].dataLim.y1 == pytest.approx(2)


def test_area_rejects_series_with_no_finite_values_after_xlim_clipping(tmp_path, monkeypatch):
    allocated = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal allocated
        allocated = True
        raise AssertionError("figure allocated")

    monkeypatch.setattr("tpsplots.views.area_chart.plt.subplots", fail_if_called)
    with pytest.raises(ValueError, match="finite value within x limits"):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=[1, 2, 3],
            y=[[1, 2, 3], [np.nan, np.nan, 4]],
            xlim=[1, 2],
            fiscal_year_ticks=False,
        )
    assert allocated is False


def test_area_inverted_xlim_clips_by_ordered_bounds_but_preserves_axis_direction(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[0, 1, 2, 3, 4],
        y=[1000, 1, 2, 3, 1000],
        xlim=[3, 1],
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    assert ax.get_xlim() == pytest.approx((3, 1))
    assert ax.dataLim.y1 == pytest.approx(3)


def test_area_applies_custom_ticks_formats_scale_and_grid_dict(tmp_path):
    fig = _view(tmp_path)._create_chart(
        metadata={"title": "T"},
        style=AreaChartView.DESKTOP,
        x=[2020, 2021, 2022],
        y=[1_000_000, 2_000_000, 3_000_000],
        xticks=[2020, 2022],
        xticklabels=["Start", "End"],
        y_tick_format=",.1f",
        scale="millions",
        grid={"axis": "x", "alpha": 0.25},
        fiscal_year_ticks=False,
    )

    ax = fig.axes[0]
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["Start", "End"]
    assert isinstance(ax.yaxis.get_major_formatter(), FuncFormatter)
    assert any(line.get_visible() for line in ax.get_xgridlines())


def test_area_create_figure_supports_annotations(tmp_path):
    fig = _view(tmp_path).create_figure(
        metadata={
            "title": "T",
            "annotations": [{"x": 2, "y": 2, "text": "Milestone"}],
        },
        x=[1, 2, 3],
        y=[1, 2, 3],
        fiscal_year_ticks=False,
    )

    assert any(text.get_text() == "Milestone" for text in fig.axes[0].texts)


def test_area_create_figure_closes_figure_when_overlay_rendering_fails(tmp_path, monkeypatch):
    view = _view(tmp_path)
    before = set(plt.get_fignums())

    def fail_overlay(*_args, **_kwargs):
        raise RuntimeError("annotation failed")

    monkeypatch.setattr(view, "_apply_annotations", fail_overlay)
    with pytest.raises(RuntimeError, match="annotation failed"):
        view.create_figure(
            metadata={"title": "T"},
            x=[1, 2],
            y=[1, 2],
            fiscal_year_ticks=False,
        )

    assert set(plt.get_fignums()) == before


def test_area_validation_happens_before_figure_allocation(tmp_path, monkeypatch):
    allocated = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal allocated
        allocated = True
        raise AssertionError("figure allocated")

    monkeypatch.setattr("tpsplots.views.area_chart.plt.subplots", fail_if_called)
    with pytest.raises(ValueError, match="same length"):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=[1, 2],
            y=[1],
            fiscal_year_ticks=False,
        )
    assert allocated is False


@pytest.mark.parametrize("key", ["baseline", "y1", "y2"])
def test_area_rejects_geometry_owned_escape_hatch_keys(tmp_path, key):
    with pytest.raises(ValueError, match=key):
        _view(tmp_path)._create_chart(
            metadata={"title": "T"},
            style=AreaChartView.DESKTOP,
            x=[1, 2],
            y=[1, 2],
            fiscal_year_ticks=False,
            **{key: 1},
        )
