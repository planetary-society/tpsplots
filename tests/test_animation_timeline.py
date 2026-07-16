"""Tests for animation timeline windows."""

import pytest

from tpsplots.animation.easing import back_out, cubic_out, linear
from tpsplots.animation.timeline import Timeline, Window


def test_window_progress_before_mid_after():
    """Progress is 0 before start, eased in the middle, 1 at/after end."""
    window = Window(start=1.0, duration=2.0, easing=linear)
    assert window.progress(0.0) == 0.0
    assert window.progress(1.0) == 0.0
    assert window.progress(2.0) == pytest.approx(0.5)
    assert window.progress(3.0) == 1.0
    assert window.progress(4.0) == 1.0


def test_window_end_property():
    """end == start + duration."""
    assert Window(start=1.5, duration=2.5).end == pytest.approx(4.0)


def test_window_eased_mid_matches_easing_call():
    """The mid-window value equals calling the easing on the local fraction."""
    window = Window(start=2.0, duration=4.0, easing=cubic_out)
    # t = 3.0 -> local fraction 0.25
    assert window.progress(3.0) == pytest.approx(cubic_out(0.25))


def test_window_zero_duration_is_a_step():
    """A zero-duration window steps from 0 to 1 exactly at start."""
    window = Window(start=2.0, duration=0.0)
    assert window.progress(1.999) == 0.0
    assert window.progress(2.0) == 1.0
    assert window.progress(5.0) == 1.0


def test_window_overshoot_easing_exceeds_one_mid_window():
    """An overshoot easing can return > 1.0 mid-window; it is not clamped."""
    window = Window(start=0.0, duration=1.0, easing=back_out)
    peak = max(window.progress(i / 1000) for i in range(1001))
    assert peak > 1.0


def test_window_default_easing_is_linear():
    """Windows default to linear easing."""
    window = Window(start=0.0, duration=1.0)
    assert window.progress(0.25) == pytest.approx(0.25)


def test_timeline_unknown_key_is_zero():
    """Progress for an unregistered key is 0.0."""
    timeline = Timeline()
    assert timeline.progress("missing", 5.0) == 0.0


def test_timeline_window_lookup():
    """window() returns the stored Window or None for unknown keys."""
    timeline = Timeline()
    window = Window(start=0.0, duration=1.0)
    timeline.add("a", window)
    assert timeline.window("a") is window
    assert timeline.window("b") is None


def test_timeline_progress_dispatches_to_window():
    """progress(key, t) delegates to the keyed window."""
    timeline = Timeline()
    timeline.add("a", Window(start=1.0, duration=2.0, easing=linear))
    assert timeline.progress("a", 2.0) == pytest.approx(0.5)


def test_timeline_duration_is_max_end():
    """duration is the latest end across all windows."""
    timeline = Timeline()
    timeline.add("a", Window(start=0.0, duration=2.0))
    timeline.add("b", Window(start=1.0, duration=3.0))  # ends at 4.0
    timeline.add("c", Window(start=0.5, duration=1.0))
    assert timeline.duration == pytest.approx(4.0)


def test_timeline_empty_duration_is_zero():
    """An empty timeline has duration 0.0."""
    assert Timeline().duration == 0.0


def test_timeline_re_adding_key_overwrites():
    """Re-adding a key replaces the prior window (last write wins)."""
    timeline = Timeline()
    timeline.add("a", Window(start=0.0, duration=5.0))
    timeline.add("a", Window(start=0.0, duration=1.0))
    assert timeline.window("a").duration == 1.0
    assert timeline.duration == pytest.approx(1.0)
