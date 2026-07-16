"""Timeline primitives for scheduling chart animation.

A :class:`Window` describes when a single animated element starts, how long it
takes, and which easing shapes its progress. A :class:`Timeline` maps arbitrary
keys (a series index, a ``(category, group, layer)`` tuple, ...) to windows and
answers "how far along is this element at wall-clock time ``t``?".

Progress values follow the same convention as :mod:`tpsplots.animation.easing`:
they are roughly ``[0, 1]`` but overshoot easings may briefly exceed ``1.0``
mid-window. Windows deliberately do NOT clamp - callers that drive alpha must
clamp themselves, since ``set_alpha`` rejects out-of-range values.
"""

from collections.abc import Hashable
from dataclasses import dataclass

from tpsplots.animation.easing import EasingFn, linear


@dataclass(frozen=True)
class Window:
    """A single element's animation span.

    Attributes:
        start: Wall-clock time (seconds) when the element begins animating.
        duration: How long the element takes; ``0`` makes it a step function.
        easing: Curve mapping normalized progress; defaults to :func:`linear`.
    """

    start: float
    duration: float
    easing: EasingFn = linear

    @property
    def end(self) -> float:
        """Wall-clock time when the element finishes."""
        return self.start + self.duration

    def progress(self, t: float) -> float:
        """Return eased progress at time ``t``.

        Returns ``0.0`` before :attr:`start` and ``1.0`` at or after
        :attr:`end`. In between, returns ``easing((t - start) / duration)``.
        A zero-duration window is a step: ``0.0`` before ``start`` and ``1.0``
        at or after it.

        The result is not clamped: an overshoot easing may return a value
        above ``1.0`` mid-window. That is intended; callers driving alpha must
        clamp the value themselves.

        Args:
            t: Wall-clock time in seconds.

        Returns:
            Eased progress, roughly in ``[0, 1]``.
        """
        if t < self.start:
            return 0.0
        if self.duration == 0 or t >= self.end:
            return 1.0
        return self.easing((t - self.start) / self.duration)


class Timeline:
    """A collection of keyed :class:`Window` objects sharing one clock."""

    def __init__(self) -> None:
        """Create an empty timeline."""
        self._windows: dict[Hashable, Window] = {}

    def add(self, key: Hashable, window: Window) -> None:
        """Register ``window`` under ``key``.

        Re-adding an existing key overwrites the previous window (last write
        wins).

        Args:
            key: Any hashable identifier for the animated element.
            window: The window to schedule.
        """
        self._windows[key] = window

    def progress(self, key: Hashable, t: float) -> float:
        """Return the progress of ``key`` at time ``t``.

        Unknown keys return ``0.0`` (nothing scheduled, nothing revealed).

        Args:
            key: The element identifier.
            t: Wall-clock time in seconds.

        Returns:
            Eased progress for the element, or ``0.0`` if ``key`` is unknown.
        """
        window = self._windows.get(key)
        if window is None:
            return 0.0
        return window.progress(t)

    def window(self, key: Hashable) -> Window | None:
        """Return the :class:`Window` for ``key``, or ``None`` if unknown."""
        return self._windows.get(key)

    @property
    def duration(self) -> float:
        """The latest end time across all windows; ``0.0`` when empty."""
        if not self._windows:
            return 0.0
        return max(window.end for window in self._windows.values())
