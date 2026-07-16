"""Tests for animation easing curves and the easing registry."""

import itertools

import pytest

from tpsplots.animation.easing import (
    EASINGS,
    back_out,
    back_out_soft,
    get_easing,
    glide_pop,
)

# Curves that must never dip backwards as t increases.
NON_OVERSHOOT = [
    "linear",
    "cubic_in_out",
    "quint_in_out",
    "expo_in_out",
    "cubic_out",
    "quart_out",
    "quint_out",
]


def _samples(n: int = 1000) -> list[float]:
    return [i / (n - 1) for i in range(n)]


@pytest.mark.parametrize("name", sorted(EASINGS))
def test_endpoints_are_zero_and_one(name):
    """Every easing pins f(0) == 0 and f(1) == 1."""
    fn = EASINGS[name]
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("name", NON_OVERSHOOT)
def test_non_overshoot_curves_are_monotonic(name):
    """Non-overshoot curves never decrease over a dense sample sweep."""
    fn = EASINGS[name]
    values = [fn(t) for t in _samples(1000)]
    for prev, curr in itertools.pairwise(values):
        assert curr >= prev - 1e-12


def test_back_out_soft_overshoot_is_gentle():
    """back_out_soft peaks between 1.0 and 1.06 (~3-4% overshoot)."""
    peak = max(back_out_soft(t) for t in _samples(1000))
    assert 1.0 < peak < 1.06


def test_back_out_overshoot_is_pronounced():
    """back_out peaks between 1.05 and 1.15 (~10% overshoot)."""
    peak = max(back_out(t) for t in _samples(1000))
    assert 1.05 < peak < 1.15


def test_glide_pop_starts_slow_pops_late_and_feathers_in():
    """glide_pop anticipates like an in-out, peaks ~4% over 1.0 around
    t=0.8, then feathers into 1.0 without undershooting — the
    "glide, pop, settle" shape with a quint-like landing."""
    assert glide_pop(0.25) < 0.1  # in-out anticipation
    samples = _samples(1000)
    peak_t = max(samples, key=glide_pop)
    assert 0.75 < peak_t < 0.85
    assert 1.0 < glide_pop(peak_t) < 1.06
    # Feathered landing: nearly seated well before t=1, never dipping
    # below the final value on the way back down.
    assert 1.0 < glide_pop(0.95) < 1.005


def test_registry_has_exactly_the_specified_keys():
    """The registry vocabulary is locked to the documented key set."""
    assert set(EASINGS) == {
        "linear",
        "cubic_in_out",
        "quint_in_out",
        "expo_in_out",
        "cubic_out",
        "quart_out",
        "quint_out",
        "back_out",
        "back_out_soft",
        "glide_pop",
    }


def test_get_easing_returns_the_registry_object():
    """get_easing returns the exact same function object as the registry."""
    for name, fn in EASINGS.items():
        assert get_easing(name) is fn


def test_overshoot_registry_matches_behavior():
    """OVERSHOOT_EASINGS membership <=> the curve actually exceeds 1.0.

    Guards the classification a new easing could silently miss: an overshoot
    easing outside the set would let value labels fade over a dishonest bar.
    """
    from tpsplots.animation.easing import OVERSHOOT_EASINGS

    for name, fn in EASINGS.items():
        max_progress = max(fn(i / 1000) for i in range(1001))
        overshoots = max_progress > 1.0 + 1e-12
        assert overshoots == (name in OVERSHOOT_EASINGS), (
            f"{name}: max progress {max_progress} vs OVERSHOOT_EASINGS membership"
        )


def test_get_easing_unknown_name_lists_valid_names():
    """An unknown easing name raises ValueError naming every valid easing."""
    with pytest.raises(ValueError) as excinfo:
        get_easing("nope")
    message = str(excinfo.value)
    for name in EASINGS:
        assert name in message
