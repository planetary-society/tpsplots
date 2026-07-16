"""Easing functions for chart animation timing.

Easing functions map a normalized time ``t`` in ``[0, 1]`` to an eased
progress value that is also roughly in ``[0, 1]``. "In-out" curves start
and end slowly; "out" curves launch immediately and decelerate into their
endpoint. Overshoot curves (the ``back_out`` family) briefly exceed ``1.0``
before settling, which reads as a small "pop" when applied to geometry.

These are the standard Penner-style curves, kept pure (stdlib only) so the
:mod:`tpsplots.animation` package stays cheap to import.

Usage:
    from tpsplots.animation.easing import get_easing, EASINGS

    ease = get_easing("cubic_out")
    progress = ease(0.5)
"""

from collections.abc import Callable

# An easing function maps normalized time t in [0, 1] to progress ~[0, 1].
# Overshoot curves may return values slightly above 1.0 mid-range.
EasingFn = Callable[[float], float]


def linear(t: float) -> float:
    """Return ``t`` unchanged (constant velocity, no easing)."""
    return t


def cubic_in_out(t: float) -> float:
    """Ease with a slow start and slow end (symmetric cubic S-curve)."""
    if t < 0.5:
        return 4 * t**3
    return 1 - (-2 * t + 2) ** 3 / 2


def quint_in_out(t: float) -> float:
    """Ease with a slow start and slow end, sharper than :func:`cubic_in_out`.

    The higher exponent holds the anticipation longer and rushes the middle
    harder — the broadcast-graphics "glide into place" S-curve.
    """
    if t < 0.5:
        return 16 * t**5
    return 1 - (-2 * t + 2) ** 5 / 2


# Raw Penner expo curves leave a 2**-10 residual; expo_in_out rescales it away.
_EXPO_RESIDUAL = 2.0**-10


def expo_in_out(t: float) -> float:
    """Ease exponentially in and out: the sharpest S-curve short of a cut.

    Matches the heavy incoming/outgoing ease influence After Effects motion
    designers use for chart builds. Normalized so the endpoints are exactly
    0 and 1 (the raw Penner form misses by ``2**-11`` at each end).
    """
    raw = 2.0 ** (20.0 * t - 10.0) / 2.0 if t < 0.5 else (2.0 - 2.0 ** (-20.0 * t + 10.0)) / 2.0
    return (raw - _EXPO_RESIDUAL / 2.0) / (1.0 - _EXPO_RESIDUAL)


def cubic_out(t: float) -> float:
    """Ease out cubically: launch immediately, decelerate into the endpoint."""
    return 1 - (1 - t) ** 3


def quart_out(t: float) -> float:
    """Ease out quartically: sharper deceleration than :func:`cubic_out`."""
    return 1 - (1 - t) ** 4


def quint_out(t: float) -> float:
    """Ease out quintically: the sharpest launch/settle of the out family.

    The default motion easing — a near-instant launch that spends most of the
    window decelerating into the endpoint.
    """
    return 1 - (1 - t) ** 5


def back_out(t: float, s: float = 1.70158) -> float:
    """Ease out with overshoot: settle past ``1.0`` then back (~10% overshoot).

    Args:
        t: Normalized time in ``[0, 1]``.
        s: Overshoot tension; the default ``1.70158`` gives roughly 10%
            overshoot, the classic Penner value.

    Returns:
        Eased progress; peaks slightly above ``1.0`` before ``t`` reaches 1.
    """
    u = t - 1
    return 1 + u * u * ((s + 1) * u + s)


def back_out_soft(t: float) -> float:
    """Ease out with a gentle overshoot (~3-4%) using tension ``s = 0.8``.

    A softer sibling of :func:`back_out` for subtle "settle pop" motion
    where a full 10% overshoot would collide with labels or look busy.
    """
    return back_out(t, s=0.8)


def glide_pop(t: float) -> float:
    """Ease in slowly, rush the middle, overshoot ~4%, then feather in.

    A quintic back curve on a ``t**3.5`` time warp: tracks
    :func:`cubic_in_out` through the midpoint, overshoots to ~1.04 around
    ``t = 0.8``, then settles with a brief quint-like landing (quartic
    contact at ``t = 1``) instead of stopping dead — the news-graphics
    "glide, pop, settle" keyframe pattern. Overshoot curve: geometry only,
    never alpha.
    """
    s = 2.2  # tension: peaks ~4% above 1.0
    v = t**3.5 - 1.0
    return 1.0 + (s + 1.0) * v**5 + s * v**4


# Registry of named easing functions. The keys here are the single source of
# truth for the animation easing vocabulary; a parity test elsewhere asserts a
# Pydantic Literal matches this exact key set, so do not add or rename keys
# without updating that Literal.
EASINGS: dict[str, EasingFn] = {
    "linear": linear,
    "cubic_in_out": cubic_in_out,
    "quint_in_out": quint_in_out,
    "expo_in_out": expo_in_out,
    "cubic_out": cubic_out,
    "quart_out": quart_out,
    "quint_out": quint_out,
    "back_out": back_out,
    "back_out_soft": back_out_soft,
    "glide_pop": glide_pop,
}

# Easings whose progress exceeds 1.0 mid-curve. Consumers use this to keep
# overshoot away from alpha and to delay value labels until a bar has settled
# at its honest value. A test asserts membership <=> max progress > 1.0, so a
# new overshoot easing cannot silently miss this set.
OVERSHOOT_EASINGS: frozenset[str] = frozenset({"back_out", "back_out_soft", "glide_pop"})


def get_easing(name: str) -> EasingFn:
    """Look up an easing function by name.

    Args:
        name: A key from :data:`EASINGS`.

    Returns:
        The registered easing function.

    Raises:
        ValueError: If ``name`` is not a known easing; the message lists the
            valid names in sorted order.
    """
    try:
        return EASINGS[name]
    except KeyError:
        valid = ", ".join(sorted(EASINGS))
        raise ValueError(f"Unknown easing {name!r}. Valid easings: {valid}.") from None
