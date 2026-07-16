"""Tests for the bar-family animators (tpsplots.animation.animators.bars).

Covers BarAnimator (signed heights/widths, negative bars, horizontal reading
order, label fade), GroupedBarAnimator (stacked-portion timing) and
StackedBarAnimator (per-frame recomputed accumulators, label timing). Figures
are built in memory via the shared ``make_video_figure`` fixture.
"""

import pytest

from tpsplots.animation.animators.bars import (
    BarAnimator,
    GroupedBarAnimator,
    StackedBarAnimator,
)
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.views.bar_chart import BarChartView
from tpsplots.views.grouped_bar_chart import GroupedBarChartView
from tpsplots.views.stacked_bar_chart import StackedBarChartView


def _prepared(animator_cls, chart_type, fig, **overrides):
    animator = animator_cls(fig, resolve_animation(**overrides), CHOREOGRAPHY[chart_type])
    animator.prepare()  # ends at apply_global(0.0) -> apply(0)
    return animator


def _bar(animator, index):
    for j, cap in animator._bars:
        if j == index:
            return cap
    raise AssertionError(f"no captured bar {index}")


# ── BarAnimator ──────────────────────────────────────────────────────


def test_apply_zero_flattens_bars_and_hides_labels(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView,
        categories=["A", "B", "C"],
        values=[3, 5, 2],
        show_values=True,
        legend=False,
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)

    for _j, cap in animator._bars:
        assert cap.rect.get_height() == 0.0
    assert animator._labels  # value labels were captured
    for fade in animator._labels.values():
        assert fade.text.get_alpha() == 0.0


def test_mid_sweep_scales_signed_height_including_negative(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView, categories=["A", "B", "C"], values=[3, -5, 2], legend=False
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)

    neg = _bar(animator, 1)
    assert neg.extent == pytest.approx(-5.0)  # signed final extent
    assert neg.rect.get_y() == 0  # baseline anchor

    window = animator.timeline.window(("bar", 1))
    t = window.start + window.duration / 2
    animator.apply(t)
    p = animator.timeline.progress(("bar", 1), t)
    assert 0.0 < p < 1.0
    assert neg.rect.get_height() == pytest.approx(neg.extent * p)
    assert neg.rect.get_height() < 0  # scaling toward the negative final
    assert neg.rect.get_y() == 0  # anchor never moves


def test_horizontal_widths_animate_in_reading_order(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView,
        categories=["A", "B", "C"],
        values=[3, 5, 2],
        orientation="horizontal",
        legend=False,
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)
    n = len(animator._bars)
    assert n == 3

    # barh index 0 is at the bottom; reading order is top->bottom, so the LAST
    # index (top) starts before index 0 (bottom).
    assert (
        animator.timeline.window(("bar", n - 1)).start < animator.timeline.window(("bar", 0)).start
    )

    cap = _bar(animator, 0)
    assert cap.orient == "h"
    assert cap.rect.get_width() == 0.0  # apply(0)
    window = animator.timeline.window(("bar", 0))
    animator.apply(window.start + window.duration / 2)
    assert 0.0 < abs(cap.rect.get_width()) < abs(cap.extent)
    assert cap.rect.get_x() == 0  # baseline anchor unchanged


def test_finalize_matches_captured_extents_exactly(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView, categories=["A", "B", "C"], values=[3, -5, 2], legend=False
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)
    animator.apply(0.4)  # disturb
    animator.finalize()
    for _j, cap in animator._bars:
        assert cap.rect.get_height() == cap.extent


def test_apply_is_idempotent(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView,
        categories=["A", "B", "C"],
        values=[3, 5, 2],
        show_values=True,
        legend=False,
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)
    window = animator.timeline.window(("bar", 1))
    t = window.start + window.duration / 3

    animator.apply(t)
    first = [cap.rect.get_height() for _j, cap in animator._bars]
    animator.apply(animator.timeline.duration)  # move away
    animator.apply(t)  # and back
    assert [cap.rect.get_height() for _j, cap in animator._bars] == first


def test_value_label_fades_at_80_percent_of_bar_window(make_video_figure):
    fig = make_video_figure(
        view_cls=BarChartView,
        categories=["A", "B", "C"],
        values=[3, 5, 2],
        show_values=True,
        legend=False,
    )
    animator = _prepared(BarAnimator, "bar_plot", fig)
    bar_window = animator.timeline.window(("bar", 0))
    label_window = animator.timeline.window(("label", 0))
    assert label_window.start == pytest.approx(bar_window.start + 0.8 * bar_window.duration)

    fade = animator._labels[0]
    animator.apply(label_window.start - 0.01)
    assert fade.text.get_alpha() == 0.0
    animator.apply(label_window.end + 0.01)
    assert fade.text.get_alpha() == fade.base


def test_value_label_waits_for_settle_under_overshoot_easing(make_video_figure):
    """With an overshoot easing, labels wait for 100% of the bar window (a
    paused overshoot frame must not show a label over a dishonest bar)."""
    fig = make_video_figure(
        view_cls=BarChartView,
        categories=["A", "B"],
        values=[3, 5],
        show_values=True,
        legend=False,
    )
    animator = _prepared(BarAnimator, "bar_plot", fig, easing="back_out_soft")
    bar_window = animator.timeline.window(("bar", 0))
    label_window = animator.timeline.window(("label", 0))
    assert label_window.start == pytest.approx(bar_window.end)


# ── GroupedBarAnimator ───────────────────────────────────────────────


def _grouped_fig(make_video_figure):
    # Group G1 stacks a portion on the last category -> layer 1 exists there.
    return make_video_figure(
        view_cls=GroupedBarChartView,
        categories=["A", "B"],
        groups=[
            {"label": "G1", "values": [1, 2], "stacked_values": [3]},
            {"label": "G2", "values": [3, 4]},
        ],
        show_values=True,
    )


def test_grouped_layer1_starts_after_layer0_ends(make_video_figure):
    animator = _prepared(GroupedBarAnimator, "grouped_bar_plot", _grouped_fig(make_video_figure))
    base = animator.timeline.window(("bar", 1, 0, 0))  # category B, group G1, base
    stacked = animator.timeline.window(("bar", 1, 0, 1))  # stacked portion
    assert stacked is not None
    assert stacked.start >= base.end
    assert stacked.start == pytest.approx(base.end + 0.05)


def test_grouped_apply_zero_then_finalize(make_video_figure):
    animator = _prepared(GroupedBarAnimator, "grouped_bar_plot", _grouped_fig(make_video_figure))
    for _key, (rect, _extent) in animator._bars:
        assert rect.get_height() == 0.0
    animator.finalize()
    for _key, (rect, extent) in animator._bars:
        assert rect.get_height() == extent


# ── StackedBarAnimator ───────────────────────────────────────────────


def _stacked_fig(make_video_figure):
    return make_video_figure(
        view_cls=StackedBarChartView,
        categories=["A", "B", "C"],
        values={"X": [1, 2, 3], "Y": [4, 5, 6]},
        show_values=True,
        stack_labels=True,
        legend=False,
    )


def _stacked_rects(animator):
    """All (category, layer, rect) triples from the animator's capture."""
    return [(j, k, rect) for j, segs in animator._stacks.items() for k, rect, _extent in segs]


def test_stacked_segments_stay_seated_at_mid_t(make_video_figure):
    animator = _prepared(StackedBarAnimator, "stacked_bar_plot", _stacked_fig(make_video_figure))
    # A time inside BOTH layer windows' overlap (they overlap by construction:
    # layer_offset < layer_duration), so both layers are mid-growth at once —
    # derived from the timeline so choreography retunes can't break the test.
    layer0 = animator.timeline.window(("layer", 0))
    layer1 = animator.timeline.window(("layer", 1))
    assert layer1.start < layer0.end, "layers must overlap for this test"
    t = (layer1.start + layer0.end) / 2
    animator.apply(t)

    # Observable seating invariant: each rect sits exactly on the one below it
    # (its y is the previous rect's y + its rendered height), starting from the
    # category baseline, and heights equal extent * eased layer progress.
    for j, segments in animator._stacks.items():
        bottom = animator._baseline[j]
        for k, rect, extent in segments:
            p = animator.timeline.progress(("layer", k), t)
            assert 0.0 < p < 1.0  # the chosen t is mid-flight for both layers
            assert rect.get_y() == pytest.approx(bottom)
            assert rect.get_height() == pytest.approx(extent * p)
            bottom += rect.get_height()


def test_stacked_labels_appear_only_after_last_layer(make_video_figure):
    animator = _prepared(StackedBarAnimator, "stacked_bar_plot", _stacked_fig(make_video_figure))
    layer_offset = CHOREOGRAPHY["stacked_bar_plot"]["layer_offset"]
    layer_duration = CHOREOGRAPHY["stacked_bar_plot"]["layer_duration"]
    last_end = max(animator._layer_order) * layer_offset + layer_duration

    assert animator._label_fades  # segment + stack labels were captured
    animator.apply(last_end - 0.01)
    for fade in animator._label_fades:
        assert fade.text.get_alpha() == 0.0

    animator.apply(animator.timeline.duration)
    for fade in animator._label_fades:
        assert fade.text.get_alpha() == fade.base


def test_stacked_finalize_restores_exact_geometry(make_video_figure):
    fig = _stacked_fig(make_video_figure)
    # Record the fully-rendered geometry BEFORE the animator touches anything.
    from tpsplots.views.anim_tags import Roles, iter_tagged

    original = {
        id(rect): (rect.get_y(), rect.get_height())
        for tag, rect in iter_tagged(fig)
        if tag.role == Roles.BAR_SEGMENT
    }

    animator = _prepared(StackedBarAnimator, "stacked_bar_plot", fig)
    animator.apply(1.0)  # disturb
    animator.finalize()
    for _j, _k, rect in _stacked_rects(animator):
        y, height = original[id(rect)]
        assert rect.get_y() == pytest.approx(y)
        assert rect.get_height() == pytest.approx(height)


def test_stacked_apply_is_idempotent(make_video_figure):
    animator = _prepared(StackedBarAnimator, "stacked_bar_plot", _stacked_fig(make_video_figure))
    t = 0.9

    def snapshot():
        return {
            (j, k): (rect.get_y(), rect.get_height()) for j, k, rect in _stacked_rects(animator)
        }

    animator.apply(t)
    first = snapshot()
    animator.apply(animator.timeline.duration)
    animator.apply(t)
    assert snapshot() == first
