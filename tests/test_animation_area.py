"""Tests for collection-clipped area chart animation."""

import numpy as np
import pytest
from matplotlib.transforms import Bbox

from tpsplots.animation.animators.area import AreaAnimator
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.views import AreaChartView
from tpsplots.views.anim_tags import Roles


def _figure(make_video_figure, **kwargs):
    params = {
        "view_cls": AreaChartView,
        "x": [1, 2, 3, 4],
        "y": [[1, 2, 1, 3], [2, 1, 3, 2]],
        "legend": False,
        "fiscal_year_ticks": False,
    }
    params.update(kwargs)
    return make_video_figure(**params)


def _prepared(fig, **overrides):
    animator = AreaAnimator(fig, resolve_animation(**overrides), CHOREOGRAPHY["area_plot"])
    animator.prepare()
    return animator


def _mid_time(animator):
    window = animator.timeline.window(("area", 0))
    return window.start + window.duration / 2


def test_area_animator_discovers_all_collections_and_uses_one_window(make_video_figure):
    animator = _prepared(_figure(make_video_figure, stacked=True))

    assert len(animator.tagged(Roles.SERIES)) == 2
    assert animator.timeline.window(("area", 0)) is not None
    assert animator.timeline.window(("area", 1)) is None


def test_partial_frame_gives_every_stacked_layer_the_same_frontier(make_video_figure):
    animator = _prepared(_figure(make_video_figure, stacked=True))
    animator.apply(_mid_time(animator))

    extents = [capture.collection.get_clip_box().extents for capture in animator._areas]
    np.testing.assert_allclose(extents[0], extents[1])
    axes_box = animator._areas[0].collection.axes.bbox
    assert axes_box.x0 < extents[0][2] < axes_box.x1


def test_animation_never_mutates_area_polygon_paths(make_video_figure):
    fig = _figure(make_video_figure, stacked=True)
    original = [
        [path.vertices.copy() for path in collection.get_paths()]
        for collection in fig.axes[0].collections
    ]
    animator = _prepared(fig)

    animator.apply(_mid_time(animator))
    animator.finalize()
    for collection, expected_paths in zip(fig.axes[0].collections, original, strict=True):
        for path, expected in zip(collection.get_paths(), expected_paths, strict=True):
            np.testing.assert_array_equal(path.vertices, expected)


def test_finalize_restores_exact_collection_clip_state(make_video_figure):
    fig = _figure(make_video_figure)
    first = fig.axes[0].collections[0]
    custom_box = Bbox.from_extents(10, 20, 300, 400)
    first.set_clip_on(False)
    first.set_clip_box(custom_box)

    animator = _prepared(fig)
    captured = animator._areas[0]
    animator.apply(_mid_time(animator))
    assert first.get_clip_on() is True
    animator.finalize()

    assert first.get_clip_on() is captured.clip_on is False
    assert first.get_clip_box() is captured.clip_box
    assert first.get_clip_path() is captured.clip_path


def test_backward_seeking_and_repeated_time_are_idempotent(make_video_figure):
    animator = _prepared(_figure(make_video_figure))
    middle = _mid_time(animator)
    animator.apply(middle)
    first = animator._areas[0].collection.get_clip_box().extents.copy()
    animator.apply(animator.timeline.duration)
    animator.apply(middle)
    second = animator._areas[0].collection.get_clip_box().extents.copy()
    animator.apply(middle)
    third = animator._areas[0].collection.get_clip_box().extents.copy()

    np.testing.assert_allclose(first, second)
    np.testing.assert_allclose(second, third)


def test_overshoot_easing_is_clamped_to_axes_bounds(make_video_figure):
    animator = _prepared(_figure(make_video_figure), easing="back_out_soft")
    axes_box = animator._areas[0].collection.axes.bbox
    window = animator.timeline.window(("area", 0))

    for fraction in np.linspace(0, 1, 21):
        animator.apply(window.start + fraction * window.duration)
        clip_box = animator._areas[0].collection.get_clip_box()
        assert clip_box.x0 >= axes_box.x0 - 1e-9
        assert clip_box.x1 <= axes_box.x1 + 1e-9


@pytest.mark.parametrize(
    "x",
    [
        ["A", "B", "C", "D"],
        np.array(["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"], dtype="datetime64[D]"),
    ],
)
def test_area_animation_supports_categorical_and_datetime_axes(make_video_figure, x):
    animator = _prepared(_figure(make_video_figure, x=x))
    animator.apply(_mid_time(animator))
    animator.finalize()


def test_finalize_restores_pre_animation_rgba_buffer(make_video_figure):
    fig = _figure(make_video_figure)
    fig.canvas.draw()
    expected = np.asarray(fig.canvas.buffer_rgba()).copy()
    animator = _prepared(fig)
    animator.apply(_mid_time(animator))
    animator.finalize()
    fig.canvas.draw()

    np.testing.assert_array_equal(np.asarray(fig.canvas.buffer_rgba()), expected)
