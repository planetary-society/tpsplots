"""Base lifecycle for chart animators.

An animator receives a fully rendered figure (built once via
``ChartView.create_figure`` with a ``video_*`` device) and animates it by
mutating artist properties frame by frame — it never re-renders the chart, so
axis limits, layout, and final label positions stay rock-solid across frames.

Lifecycle (driven by the renderer):

1. ``prepare()`` — draw once, sanity-check pixel dimensions, freeze axis
   limits, collect tagged artists (see :mod:`tpsplots.views.anim_tags`),
   build the timeline, capture final artist state, jump to t=0.
2. ``apply_global(t)`` per frame — the subclass's ``apply()`` on the
   draw-phase clock (t minus the intro hold).
3. ``finalize()`` — restore the exact captured final state for the end hold
   (and the poster frame).

Everything untagged — axes, tick labels, gridlines, legends — is fully
visible from frame 0; only the data artists (and their inline labels)
animate. The intro hold is a brief still moment before the data draw starts.

Subclasses implement :meth:`build_timeline`, :meth:`capture`, and
:meth:`apply`. ``apply(t)`` MUST be idempotent — pure state = f(t), never an
increment — so frames can be re-applied or scrubbed.

Alpha rule: ``Artist.set_alpha`` raises ``ValueError`` outside [0, 1], so any
animated alpha must go through :meth:`BaseAnimator.clamp01` (or
:class:`AlphaFade` / :class:`TextFade`, which clamp internally). Overshoot
easings may only ever drive geometry.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tpsplots.animation.config import ResolvedAnimation, effective_choreography
from tpsplots.animation.easing import EasingFn, get_easing
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.exceptions import RenderingError
from tpsplots.views.anim_tags import Tag, iter_tagged


def clamp01(value: float) -> float:
    """Clamp to [0, 1] — mandatory for anything driving ``set_alpha``."""
    return min(max(value, 0.0), 1.0)


def _fade_alpha(artist: Any, base: float | None, progress: float) -> None:
    """Fade-or-restore rule shared by every animated alpha.

    At ``progress >= 1.0`` the captured base is restored exactly — including
    ``None``, matplotlib's "alpha comes from the color". Mid-fade, ``None``
    is treated as 1.0 and the scaled value is clamped (``set_alpha`` raises
    outside [0, 1]).
    """
    if progress >= 1.0:
        artist.set_alpha(base)
    else:
        artist.set_alpha(clamp01((1.0 if base is None else base) * progress))


@dataclass
class AlphaFade:
    """Fade a single artist's alpha from 0 to its captured base value."""

    artist: Any
    base: float | None

    @classmethod
    def capture(cls, artist: Any) -> AlphaFade:
        return cls(artist, artist.get_alpha())

    def apply(self, progress: float) -> None:
        _fade_alpha(self.artist, self.base, progress)


@dataclass
class TextFade:
    """Fade a Text artist including its bbox patch (if it has one).

    ``Text.set_alpha`` does not touch the label's bbox — a direct line label
    with ``bbox=dict(..., alpha=0.8)`` would show a solid box from frame 0
    unless the patch alpha is driven too. The patch is re-fetched per apply so
    one that materializes after capture is still driven.
    """

    text: Any
    base: float | None
    bbox_base: float | None

    @classmethod
    def capture(cls, text: Any) -> TextFade:
        bbox = text.get_bbox_patch()
        return cls(text, text.get_alpha(), bbox.get_alpha() if bbox is not None else None)

    def apply(self, progress: float) -> None:
        _fade_alpha(self.text, self.base, progress)
        bbox = self.text.get_bbox_patch()
        if bbox is not None:
            _fade_alpha(bbox, self.bbox_base, progress)


class BaseAnimator(ABC):
    """Drives one figure through intro → draw → hold on a single clock."""

    def __init__(
        self,
        fig: Any,
        anim: ResolvedAnimation,
        choreo: Mapping[str, Any],
        expected_px: tuple[int, int] | None = None,
    ) -> None:
        """
        Args:
            fig: The fully rendered figure to animate (from ``create_figure``).
            anim: Resolved global animation settings.
            choreo: Per-chart-type constants from ``CHOREOGRAPHY``; the user's
                ``duration``/``stagger``/``easing`` overrides are folded in for
                keys the choreography actually defines.
            expected_px: Expected (width, height) pixel dimensions; when given,
                ``prepare()`` fails loudly on a mismatch (catches the silent
                unknown-device → DESKTOP fallback in ``create_figure``).
        """
        self.fig = fig
        self.anim = anim
        self.choreo = effective_choreography(choreo, anim)
        self.expected_px = expected_px
        self.by_role: dict[str, list[tuple[Tag, Any]]] = {}
        self.timeline = Timeline()
        self._draw_duration = 0.0

    # ── lifecycle ────────────────────────────────────────────────────

    def prepare(self) -> None:
        """Draw once, freeze the scene, capture final state, jump to t=0."""
        self.fig.canvas.draw()  # renderer + unit-conversion caches
        self._assert_pixel_dims()
        self._cap_portrait_panel()
        self._freeze_axes_limits()
        self._collect_tagged()
        self.timeline = self.build_timeline()
        self._draw_duration = self.timeline.duration  # frozen; hoisted off the frame loop
        self.capture()
        self.apply_global(0.0)

    def apply_global(self, t: float) -> None:
        """Advance the whole scene to wall-clock time ``t`` (idempotent)."""
        draw_t = min(max(t - self.anim.intro_hold, 0.0), self._draw_duration)
        self.apply(draw_t)

    def finalize(self) -> None:
        """Restore the exact final state (for the end hold / poster frame)."""
        self.apply(self._draw_duration)

    @property
    def total_duration(self) -> float:
        """Video length in seconds: intro + draw phase + end hold."""
        return self.anim.intro_hold + self._draw_duration + self.anim.end_hold

    # ── subclass contract ────────────────────────────────────────────

    @abstractmethod
    def build_timeline(self) -> Timeline:
        """Schedule a Window per animated element (draw-phase clock)."""

    @abstractmethod
    def capture(self) -> None:
        """Snapshot the FINAL state of every animated artist."""

    @abstractmethod
    def apply(self, t: float) -> None:
        """Set every animated artist's state for draw-phase time ``t``.

        Must be idempotent: state = f(t), never f(dt).
        """

    # ── shared helpers ───────────────────────────────────────────────

    # Part of the subclass API (also available module-level).
    clamp01 = staticmethod(clamp01)

    def tagged(self, role: str) -> list[tuple[Tag, Any]]:
        """Tagged ``(tag, artist)`` pairs for ``role``, sorted by tag index."""
        return self.by_role.get(role, [])

    def choreo_easing(self, key: str, fallback: str = "linear") -> EasingFn:
        """Resolve an easing name stored in the choreography to a function."""
        return get_easing(self.choreo.get(key) or fallback)

    def label_fade_window(self, start: float) -> Window:
        """A value-label fade Window using the choreography's duration/easing.

        The single construction point for label fades: duration from
        ``label_fade``, easing from ``label_fade_easing`` (both tunable in
        ``CHOREOGRAPHY``).
        """
        return Window(
            start,
            float(self.choreo["label_fade"]),
            self.choreo_easing("label_fade_easing", "cubic_out"),
        )

    # ── internals ────────────────────────────────────────────────────

    def _assert_pixel_dims(self) -> None:
        if self.expected_px is None:
            return
        width, height = (round(v) for v in self.fig.get_size_inches() * self.fig.dpi)
        if (width, height) != self.expected_px:
            raise RenderingError(
                f"Video frame is {width}x{height}px, expected "
                f"{self.expected_px[0]}x{self.expected_px[1]}px — the figure was "
                "not built with the requested video device style."
            )

    def _cap_portrait_panel(self) -> None:
        """Cap the axes panel to <=1:1 in portrait frames.

        A full-height plot panel in a 9:16 frame wildly exaggerates slopes
        (banking-to-45 violation). Shrink each taller-than-wide axes to a
        square panel and center it vertically, leaving breathing room for
        editor-added captions. Safe post-layout: the one-shot tight_layout has
        already run, and manual ``set_position`` survives redraws.
        """
        fig_width_in, fig_height_in = self.fig.get_size_inches()
        if fig_height_in <= fig_width_in:
            return
        for ax in self.fig.get_axes():
            pos = ax.get_position()
            panel_width_in = pos.width * fig_width_in
            panel_height_in = pos.height * fig_height_in
            if panel_height_in <= panel_width_in:
                continue
            new_height = panel_width_in / fig_height_in  # square panel, fig fraction
            new_y0 = pos.y0 + (pos.height - new_height) / 2
            ax.set_position([pos.x0, new_y0, pos.width, new_height])

    def _freeze_axes_limits(self) -> None:
        """Pin limits (and disable autoscale) on every axes, twinx included."""
        for ax in self.fig.get_axes():
            ax.set_xlim(ax.get_xlim())
            ax.set_ylim(ax.get_ylim())

    def _collect_tagged(self) -> None:
        self.by_role = {}
        for tag, artist in iter_tagged(self.fig):
            self.by_role.setdefault(tag.role, []).append((tag, artist))
        for pairs in self.by_role.values():
            pairs.sort(key=lambda pair: pair[0].index)
