"""Tests for LollipopAnimator (tpsplots.animation.animators.lollipop).

Covers the stem grow (zero length at t=0, endpoint between start/end mid-sweep),
the end-marker pop (invisible before its window, sizes/alpha restored at
finalize), label fades, and idempotency. Figures are built in memory via the
shared ``make_video_figure`` fixture.
"""

import numpy as np
import pytest

from tpsplots.animation.animators.lollipop import LollipopAnimator
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.views.lollipop_chart import LollipopChartView

CATEGORIES = ["A", "B"]
START = [1, 2]
END = [5, 6]


def _fig(make_video_figure, **extra):
    return make_video_figure(
        view_cls=LollipopChartView,
        categories=CATEGORIES,
        start_values=START,
        end_values=END,
        **extra,
    )


def _prepared(fig, **overrides):
    animator = LollipopAnimator(fig, resolve_animation(**overrides), CHOREOGRAPHY["lollipop_plot"])
    animator.prepare()  # ends at apply_global(0.0) -> apply(0)
    return animator


def _stem(animator, index):
    for i, cap in animator._stems:
        if i == index:
            return cap
    raise AssertionError(f"no captured stem {index}")


def _end_marker(animator, index):
    for i, cap in animator._end_markers:
        if i == index:
            return cap
    raise AssertionError(f"no captured end marker {index}")


# ── stems ────────────────────────────────────────────────────────────


def test_stem_zero_length_at_t0(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    for _i, cap in animator._stems:
        x = np.asarray(cap.line.get_xdata(), dtype=float)
        y = np.asarray(cap.line.get_ydata(), dtype=float)
        if cap.axis == "x":
            assert x[0] == x[-1] == pytest.approx(cap.base)
        else:
            assert y[0] == y[-1] == pytest.approx(cap.base)


def test_stem_endpoint_between_start_and_end_mid_sweep(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    cap = _stem(animator, 0)
    assert cap.axis == "x"  # lollipop stems are horizontal
    window = animator.timeline.window(("stem", 0))
    animator.apply(window.start + window.duration / 2)

    x = np.asarray(cap.line.get_xdata(), dtype=float)
    cur = x[-1]  # the growing endpoint
    lo, hi = sorted((cap.base, cap.end))
    assert lo < cur < hi
    assert x[0] == pytest.approx(cap.base)  # origin pinned


def test_stem_grows_monotonically(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    cap = _stem(animator, 0)
    window = animator.timeline.window(("stem", 0))
    lengths = []
    for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
        animator.apply(window.start + fraction * window.duration)
        x = np.asarray(cap.line.get_xdata(), dtype=float)
        lengths.append(abs(x[-1] - cap.base))
    assert lengths == sorted(lengths)


# ── end markers ──────────────────────────────────────────────────────


def test_end_marker_hidden_before_pop(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    # apply(0) is before every pop window (which starts at the stem end).
    for _i, cap in animator._end_markers:
        assert cap.collection.get_alpha() == 0.0


def test_end_marker_alpha_stays_clamped_through_pop(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    cap = _end_marker(animator, 0)
    window = animator.timeline.window(("pop", 0))
    for fraction in (0.25, 0.5, 0.75, 0.999):
        animator.apply(window.start + fraction * window.duration)
        alpha = cap.collection.get_alpha()
        assert alpha is None or 0.0 <= alpha <= 1.0


def test_finalize_restores_sizes_and_alpha(make_video_figure):
    animator = _prepared(_fig(make_video_figure))
    animator.apply(0.3)  # disturb
    animator.finalize()
    for _i, cap in animator._end_markers:
        np.testing.assert_allclose(cap.collection.get_sizes(), cap.final_sizes)
        assert cap.collection.get_alpha() == cap.fade.base
    for _i, cap in animator._stems:
        x = np.asarray(cap.line.get_xdata(), dtype=float)
        y = np.asarray(cap.line.get_ydata(), dtype=float)
        if cap.axis == "x":
            np.testing.assert_allclose(x, [cap.base, cap.end])
            np.testing.assert_allclose(y, [cap.const, cap.const])
        else:
            np.testing.assert_allclose(x, [cap.const, cap.const])
            np.testing.assert_allclose(y, [cap.base, cap.end])


# ── labels ───────────────────────────────────────────────────────────


def test_value_labels_fade_at_stem_completion(make_video_figure):
    animator = _prepared(_fig(make_video_figure, value_labels=True))
    assert animator._labels  # start + end labels per category
    window = animator.timeline.window(("label", 0))
    assert window.start == pytest.approx(animator.timeline.window(("stem", 0)).end)

    animator.apply(window.start - 0.01)
    for i, fade in animator._labels:
        if i == 0:
            assert fade.text.get_alpha() == 0.0

    animator.apply(window.end + 0.01)
    for i, fade in animator._labels:
        if i == 0:
            assert fade.text.get_alpha() == fade.base


# ── idempotency ──────────────────────────────────────────────────────


def test_apply_is_idempotent(make_video_figure):
    animator = _prepared(_fig(make_video_figure, value_labels=True))
    t = 0.6
    animator.apply(t)
    stem_first = np.asarray(_stem(animator, 0).line.get_xdata(), dtype=float).copy()
    size_first = np.array(_end_marker(animator, 0).collection.get_sizes(), dtype=float)

    animator.apply(animator.timeline.duration)  # move away
    animator.apply(t)  # and back
    np.testing.assert_allclose(
        np.asarray(_stem(animator, 0).line.get_xdata(), dtype=float), stem_first
    )
    np.testing.assert_allclose(
        np.array(_end_marker(animator, 0).collection.get_sizes(), dtype=float), size_first
    )
