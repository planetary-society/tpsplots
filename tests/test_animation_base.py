"""Tests for the BaseAnimator lifecycle (tpsplots.animation.animators.base)."""

import matplotlib.pyplot as plt
import pytest

from tpsplots.animation.animators import (
    UnsupportedChartAnimation,
    get_animator,
    supported_chart_types,
)
from tpsplots.animation.animators.base import AlphaFade, BaseAnimator, TextFade
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.exceptions import RenderingError
from tpsplots.views.anim_tags import Roles


class _NullAnimator(BaseAnimator):
    """Minimal concrete animator: one 1s window, records apply() calls."""

    def build_timeline(self):
        timeline = Timeline()
        timeline.add("only", Window(0.0, 1.0))
        return timeline

    def capture(self):
        self.captured = True

    def apply(self, t):
        self.last_t = t


def _animator(fig, expected_px=None, **overrides):
    anim = resolve_animation(**overrides)
    return _NullAnimator(fig, anim, CHOREOGRAPHY["line_plot"], expected_px=expected_px)


# ── prepare() ────────────────────────────────────────────────────────


def test_prepare_freezes_limits_and_disables_autoscale(make_video_figure):
    fig = make_video_figure()
    animator = _animator(fig)
    animator.prepare()
    for ax in fig.get_axes():
        assert not ax.get_autoscalex_on()
        assert not ax.get_autoscaley_on()


def test_prepare_collects_tagged_artists_sorted(make_video_figure):
    fig = make_video_figure(y=[[1, 2, 3], [2, 3, 4]])
    animator = _animator(fig)
    animator.prepare()
    series = animator.tagged(Roles.SERIES)
    assert [tag.index for tag, _ in series] == [0, 1]
    assert animator.captured
    assert animator.last_t == 0.0  # prepare ends at t=0


def test_pixel_dim_assertion(make_video_figure):
    fig = make_video_figure()
    _animator(fig, expected_px=(1080, 1080)).prepare()  # matches: no raise
    with pytest.raises(RenderingError, match="1080x1080"):
        _animator(fig, expected_px=(1920, 1080)).prepare()


def test_portrait_panel_capped_to_square(make_video_figure):
    fig = make_video_figure(device="video_portrait")
    animator = _animator(fig, expected_px=(1080, 1920))
    animator.prepare()
    fig_w, fig_h = fig.get_size_inches()
    for ax in fig.get_axes():
        pos = ax.get_position()
        assert pos.height * fig_h <= pos.width * fig_w + 1e-6


def test_landscape_panel_not_capped(make_video_figure):
    fig = make_video_figure(device="video_landscape")
    before = [tuple(ax.get_position().bounds) for ax in fig.get_axes()]
    animator = _animator(fig)
    animator.prepare()
    after = [tuple(ax.get_position().bounds) for ax in fig.get_axes()]
    assert before == after


# ── static chrome ────────────────────────────────────────────────────


def _chrome_alphas(fig):
    """Alpha of every gridline and tick label across all axes."""
    artists = []
    for ax in fig.get_axes():
        artists.extend(ax.get_xgridlines())
        artists.extend(ax.get_ygridlines())
        artists.extend(ax.get_xticklabels())
        artists.extend(ax.get_yticklabels())
    return [artist.get_alpha() for artist in artists]


def test_chrome_is_fully_visible_from_frame_zero(make_video_figure):
    """Axes, tick labels, and gridlines are never animated — their alphas are
    untouched at t=0 and every later time; only tagged data artists move."""
    fig = make_video_figure()
    original = _chrome_alphas(fig)
    assert original, "expected gridlines/ticklabels present"

    animator = _animator(fig)
    animator.prepare()  # ends at apply_global(0.0) — frame zero
    assert _chrome_alphas(fig) == original

    animator.apply_global(animator.anim.intro_hold / 2)
    assert _chrome_alphas(fig) == original

    animator.finalize()
    assert _chrome_alphas(fig) == original


# ── clocks ───────────────────────────────────────────────────────────


def test_apply_global_maps_wall_clock_to_draw_clock(make_video_figure):
    fig = make_video_figure()
    animator = _animator(fig)
    animator.prepare()
    intro = animator.anim.intro_hold

    animator.apply_global(intro + 0.5)
    assert animator.last_t == pytest.approx(0.5)

    animator.apply_global(intro + 99.0)  # deep into the end hold
    assert animator.last_t == pytest.approx(animator.timeline.duration)

    animator.apply_global(0.0)  # before the draw phase
    assert animator.last_t == 0.0


def test_total_duration_composition(make_video_figure):
    fig = make_video_figure()
    animator = _animator(fig, end_hold=2.0)
    animator.prepare()
    expected = animator.anim.intro_hold + animator.timeline.duration + 2.0
    assert animator.total_duration == pytest.approx(expected)


def test_finalize_restores_final_state(make_video_figure):
    fig = make_video_figure()
    animator = _animator(fig)
    animator.prepare()
    animator.finalize()
    assert animator.last_t == pytest.approx(animator.timeline.duration)


# ── overrides / helpers ──────────────────────────────────────────────


def test_effective_choreo_folds_user_overrides(make_video_figure):
    fig = make_video_figure()
    animator = _animator(fig, duration=9.0, stagger=1.5, easing="linear")
    assert animator.choreo["draw_duration"] == 9.0
    assert animator.choreo["stagger"] == 1.5
    assert animator.choreo["easing"] == "linear"
    # Untouched keys keep their choreography values.
    assert animator.choreo["label_fade"] == CHOREOGRAPHY["line_plot"]["label_fade"]


def test_clamp01_bounds():
    assert BaseAnimator.clamp01(-0.5) == 0.0
    assert BaseAnimator.clamp01(1.04) == 1.0  # back_out overshoot must never crash alpha
    assert BaseAnimator.clamp01(0.5) == 0.5


def test_alpha_fade_restores_exact_base():
    line = plt.Line2D([0], [0])
    line.set_alpha(None)
    fade = AlphaFade.capture(line)
    fade.apply(0.3)
    assert line.get_alpha() == pytest.approx(0.3)
    fade.apply(1.0)
    assert line.get_alpha() is None


def test_text_fade_drives_bbox_patch():
    fig, ax = plt.subplots()
    try:
        txt = ax.text(0.5, 0.5, "label", bbox={"facecolor": "white", "alpha": 0.8})
        fig.canvas.draw()  # bbox patch materializes on draw
        fade = TextFade.capture(txt)
        fade.apply(0.5)
        assert txt.get_bbox_patch().get_alpha() == pytest.approx(0.4)
        fade.apply(1.0)
        assert txt.get_bbox_patch().get_alpha() == pytest.approx(0.8)
    finally:
        plt.close(fig)


# ── registry ─────────────────────────────────────────────────────────


def test_registry_covers_the_six_animatable_types():
    assert supported_chart_types() == (
        "bar_plot",
        "grouped_bar_plot",
        "line_plot",
        "lollipop_plot",
        "scatter_plot",
        "stacked_bar_plot",
    )


def test_unsupported_chart_type_error_lists_yaml_names():
    with pytest.raises(UnsupportedChartAnimation) as excinfo:
        get_animator("donut_plot")
    message = str(excinfo.value)
    assert "'donut'" in message
    for name in ("bar", "grouped_bar", "line", "lollipop", "scatter", "stacked_bar"):
        assert name in message
