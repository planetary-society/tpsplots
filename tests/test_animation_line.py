"""Tests for LineAnimator (tpsplots.animation.animators.line).

Covers the x-parametric sweep reveal, phantom-tip suppression on
marker-bearing/scatter lines, tip-tracking labels/markers with exact
convergence, datetime axes, NaN gaps, and idempotency.
"""

from datetime import datetime

import numpy as np
import pytest

from tpsplots.animation.animators.line import LineAnimator
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.views.anim_tags import Roles
from tpsplots.views.scatter_chart import ScatterChartView

X = [1, 2, 3, 4, 5]
Y = [[1.0, 3.0, 2.0, 5.0, 4.0]]

# Newest-first row order (the common descending-CSV case).
X_DESC = [5, 4, 3, 2, 1]
Y_DESC = [[4.0, 5.0, 2.0, 3.0, 1.0]]


def _prepared(fig, chart_type="line_plot", **overrides):
    animator = LineAnimator(fig, resolve_animation(**overrides), CHOREOGRAPHY[chart_type])
    animator.prepare()
    return animator


def _win_t(animator, key, fraction):
    """Draw-phase time at ``fraction`` of the window registered under ``key``."""
    window = animator.timeline.window(key)
    return window.start + fraction * window.duration


def _mid_t(animator, index=0):
    """A draw-phase time strictly inside the series' sweep window."""
    return _win_t(animator, ("series", index), 0.5)


def _series_line(animator, index=0):
    for tag, line in animator.tagged(Roles.SERIES):
        if tag.index == index:
            return line
    raise AssertionError(f"no tagged series {index}")


def _xy(animator, index=0):
    """The series line's current (x, y) data as float arrays."""
    line = _series_line(animator, index)
    return (
        np.asarray(line.get_xdata(), dtype=float),
        np.asarray(line.get_ydata(), dtype=float),
    )


# ── reveal mechanics ─────────────────────────────────────────────────


def test_apply_zero_hides_all_data(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)  # prepare() ends at t=0

    line = _series_line(animator)
    assert line.get_xdata().size == 0

    _, capture = animator._series[0]
    assert capture.label.text.get_alpha() == 0.0
    assert capture.label.text.get_bbox_patch().get_alpha() == 0.0
    assert capture.endpoint.get_alpha() == 0.0


def test_mid_sweep_reveals_prefix_plus_tip(make_video_figure):
    fig = make_video_figure(x=X, y=Y)
    animator = _prepared(fig)
    _, capture = animator._series[0]

    animator.apply(_mid_t(animator))
    xs, ys = _xy(animator)

    assert 2 <= xs.size <= len(X) + 1  # at least one real point plus the tip
    # Tip sits exactly at the sweep front, strictly inside the x range.
    assert capture.x_lo < xs[-1] < capture.x_hi
    # All real (non-tip) points are actual data points behind the front.
    assert np.all(xs[:-1] <= xs[-1])
    # The tip y is on the segment between its boundary neighbors.
    n_real = xs.size - 1
    lo, hi = sorted((ys[n_real - 1], float(capture.y[n_real])))
    assert lo <= ys[-1] <= hi


def test_reveal_grows_monotonically(make_video_figure):
    fig = make_video_figure(x=X, y=Y)
    animator = _prepared(fig)
    window = animator.timeline.window(("series", 0))

    sizes = []
    for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
        animator.apply(window.start + fraction * window.duration)
        sizes.append(float(np.max(_series_line(animator).get_xdata(), initial=-np.inf)))
    assert sizes == sorted(sizes)


def test_finalize_restores_exact_final_state(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]

    animator.apply(_mid_t(animator))  # disturb
    animator.finalize()

    xs, ys = _xy(animator)
    np.testing.assert_allclose(xs, capture.x)
    np.testing.assert_allclose(ys, capture.y)
    assert _series_line(animator).get_markevery() == capture.orig_markevery

    assert capture.label.text.get_position() == pytest.approx(capture.label_final)
    assert capture.label.text.get_alpha() == capture.label.base
    assert capture.label.text.get_bbox_patch().get_alpha() == capture.label.bbox_base

    ex, ey = capture.endpoint_final
    assert float(capture.endpoint.get_xdata()[0]) == pytest.approx(ex)
    assert float(capture.endpoint.get_ydata()[0]) == pytest.approx(ey)
    assert capture.endpoint.get_markersize() == pytest.approx(capture.endpoint_size)


def test_apply_is_idempotent(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]
    t = _mid_t(animator)

    animator.apply(t)
    first = (
        _xy(animator)[0].copy(),
        capture.label.text.get_position(),
        capture.endpoint.get_markersize(),
    )
    animator.apply(animator.timeline.duration)  # move away
    animator.apply(t)  # and back
    np.testing.assert_allclose(_xy(animator)[0], first[0])
    assert capture.label.text.get_position() == pytest.approx(first[1])
    assert capture.endpoint.get_markersize() == pytest.approx(first[2])


# ── tip-tracking labels ──────────────────────────────────────────────


def test_label_and_marker_ride_the_tip(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]

    animator.apply(_mid_t(animator))
    xs, ys = _xy(animator)
    tip = (xs[-1], ys[-1])

    # Marker sits on the tip; label sits at tip + captured offset.
    assert float(capture.endpoint.get_xdata()[0]) == pytest.approx(tip[0])
    assert float(capture.endpoint.get_ydata()[0]) == pytest.approx(tip[1])
    lx, ly = capture.label.text.get_position()
    assert lx == pytest.approx(tip[0] + capture.label_offset[0])
    assert ly == pytest.approx(tip[1] + capture.label_offset[1])


def test_label_fades_in_during_early_sweep(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]
    fade_window = animator.timeline.window(("label", 0))

    animator.apply(fade_window.start + fade_window.duration / 2)
    mid_alpha = capture.label.text.get_alpha()
    assert 0.0 < mid_alpha < (capture.label.base or 1.0)

    animator.apply(fade_window.end + 0.01)
    assert capture.label.text.get_alpha() == capture.label.base


def test_marker_settle_pop_is_geometry_only(make_video_figure):
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]
    pop_window = animator.timeline.window(("pop", 0))

    # Riding: marker at the reduced pre-pop size.
    animator.apply(pop_window.start - 0.01)
    assert capture.endpoint.get_markersize() < capture.endpoint_size

    # Mid-pop with back_out_soft: size may exceed final (geometry overshoot OK)
    # but alpha stays clamped in [0, 1] at all times.
    for fraction in (0.25, 0.5, 0.75, 0.999):
        animator.apply(pop_window.start + fraction * pop_window.duration)
        alpha = capture.endpoint.get_alpha()
        assert alpha is None or 0.0 <= alpha <= 1.0
    animator.apply(pop_window.end)
    assert capture.endpoint.get_markersize() == pytest.approx(capture.endpoint_size)


# ── marker rules (phantom-tip guard) ─────────────────────────────────


def test_marker_bearing_line_excludes_tip_from_markers(make_video_figure):
    fig = make_video_figure(x=X, y=Y, marker="o")
    animator = _prepared(fig)

    animator.apply(_mid_t(animator))
    line = _series_line(animator)
    n_points = np.asarray(line.get_xdata()).size
    assert line.get_markevery() == slice(0, n_points - 1)  # tip unmarked

    animator.finalize()
    _, capture = animator._series[0]
    assert line.get_markevery() == capture.orig_markevery


def test_scatter_reveals_only_real_points(make_video_figure):
    fig = make_video_figure(view_cls=ScatterChartView, x=X, y=Y)
    animator = _prepared(fig, chart_type="scatter_plot")
    _, capture = animator._series[0]
    assert capture.marker_only

    animator.apply(_mid_t(animator))
    xs = np.asarray(_series_line(animator).get_xdata(), dtype=float)
    assert 0 < xs.size < len(X)
    # Every revealed x is a real data point — no interpolated tip.
    for value in xs:
        assert np.isclose(capture.x, value).any()


# ── datetime axes ────────────────────────────────────────────────────


def test_datetime_x_axis_reveals_in_converted_float_space(make_video_figure):
    dates = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]
    fig = make_video_figure(x=dates, y=[[1.0, 4.0, 2.0, 3.0]])
    animator = _prepared(fig)
    _, capture = animator._series[0]
    assert np.isfinite(capture.x).all()  # converted floats, not datetimes

    animator.apply(_mid_t(animator))
    xs = np.asarray(_series_line(animator).get_xdata(), dtype=float)
    assert xs.size > 0
    assert capture.x_lo <= xs.max() < capture.x_hi

    animator.finalize()
    np.testing.assert_allclose(
        np.asarray(_series_line(animator).get_xdata(), dtype=float), capture.x
    )


# ── descending x (newest-first CSVs) ─────────────────────────────────


def test_descending_x_gets_reverse_sweep_not_fallback(make_video_figure, caplog):
    """Monotone-descending x is reversed and swept normally (no fallback)."""
    fig = make_video_figure(x=X_DESC, y=Y_DESC)
    with caplog.at_level("WARNING"):
        animator = _prepared(fig)
    assert not any("unsorted" in record.getMessage() for record in caplog.records)

    _, capture = animator._series[0]
    assert capture.x_sorted
    assert np.all(np.diff(capture.x) > 0)  # captured in ascending order

    animator.apply(_mid_t(animator))
    xs = _xy(animator)[0]
    assert 0 < xs.size
    assert xs.max() < capture.x_hi  # sweeping left to right, not yet done

    animator.finalize()
    np.testing.assert_allclose(_xy(animator)[0], capture.x)


def test_origin_side_anchor_pins_label_instead_of_riding(make_video_figure):
    """Descending data's data-order endpoint is the LEFTMOST point — its label
    must be pinned at the final position, never dragged along the tip."""
    fig = make_video_figure(x=X_DESC, y=Y_DESC, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]
    assert not capture.ride_tip  # anchor (x=1) is in the sweep-origin half

    animator.apply(_mid_t(animator))
    assert capture.label.text.get_position() == pytest.approx(capture.label_final)
    ex, ey = capture.endpoint_final
    assert float(capture.endpoint.get_xdata()[0]) == pytest.approx(ex)
    assert float(capture.endpoint.get_ydata()[0]) == pytest.approx(ey)


def test_ascending_anchor_still_rides(make_video_figure):
    """The normal ascending case keeps tip-riding enabled."""
    fig = make_video_figure(x=X, y=Y, direct_line_labels={"end_point": True})
    animator = _prepared(fig)
    _, capture = animator._series[0]
    assert capture.ride_tip


# ── NaN gaps ─────────────────────────────────────────────────────────


def test_nan_gap_survives_reveal_and_finalize(make_video_figure):
    y_with_gap = [[1.0, 2.0, np.nan, 4.0, 5.0]]
    fig = make_video_figure(x=X, y=y_with_gap)
    animator = _prepared(fig)

    window = animator.timeline.window(("series", 0))
    for fraction in np.linspace(0.05, 0.95, 19):
        animator.apply(window.start + float(fraction) * window.duration)
        ys = np.asarray(_series_line(animator).get_ydata(), dtype=float)
        finite_ys = ys[np.isfinite(ys)]
        if finite_ys.size:
            assert finite_ys.min() >= 1.0
            assert finite_ys.max() <= 5.0

    animator.finalize()
    ys = np.asarray(_series_line(animator).get_ydata(), dtype=float)
    assert np.isnan(ys[2])  # the gap is preserved in the final frame


# ── multi-series / stagger ───────────────────────────────────────────


def test_series_simultaneous_by_default(make_video_figure):
    fig = make_video_figure(x=X, y=[[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]])
    animator = _prepared(fig)
    w0 = animator.timeline.window(("series", 0))
    w1 = animator.timeline.window(("series", 1))
    assert w0.start == w1.start == 0.0


def test_stagger_override_offsets_series_starts(make_video_figure):
    fig = make_video_figure(x=X, y=[[1, 2, 3, 4, 5], [5, 4, 3, 2, 1]])
    animator = _prepared(fig, stagger=0.6)
    assert animator.timeline.window(("series", 1)).start == pytest.approx(0.6)


def test_duration_override_scales_sweep(make_video_figure):
    fig = make_video_figure(x=X, y=Y)
    animator = _prepared(fig, duration=1.0)
    assert animator.timeline.window(("series", 0)).duration == pytest.approx(1.0)
