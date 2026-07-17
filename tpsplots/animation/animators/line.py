"""LineAnimator: x-parametric sweep reveal with tip-tracking labels.

The reveal is parameterized by **x position**, not point index: at eased
progress ``p`` every point with ``x <= x_lo + p*(x_hi - x_lo)`` is visible,
plus one interpolated tip point so motion stays smooth between samples at
60fps. Easing the sweep position (rather than per-segment) keeps tip velocity
steady regardless of data density. This requires monotone x: ascending data
sweeps directly; descending data (newest-first CSVs are common) is reversed at
capture time and swept the same way — the reversed polyline renders
identically for solid lines and markers (dash phase may differ from the static
render, and the reversed point order persists through finalize/poster).
Genuinely unsorted series fall back to an index-order reveal (honest motion
for arbitrary row order) with a logged warning.

Data is captured in matplotlib's converted float space
(``get_xdata(orig=False)`` after the prepare-time draw), which makes datetime
axes work transparently — floats pass through the units machinery unchanged.

Tip-tracking labels: a series' direct label, endpoint marker, and orbit ring
(``Roles.ENDPOINT_RING``) ride the moving tip while the line draws. The
captured offset ``label_final - endpoint_final`` already encodes the
collision-detection adjustment from the full render, so at ``p == 1`` the
label converges exactly onto its final position with no jump. Riding only
happens when the label anchors in the sweep's destination half of the x range
(the normal case); a label anchored near the sweep's origin (e.g. descending
data, whose data-order "endpoint" is the leftmost point) is pinned at its
final position and fades in on the normal label window (its region is the
first the sweep reveals).

Late-starting series: a series whose y values begin mid-axis (an all-NaN
head — common when several series share one x column) has no revealed point
until the sweep front reaches its first finite x. Its companions' fade clock
is shifted by ``companion_delay`` (the eased-sweep time of that crossing,
precomputed via easing inversion at capture) and additionally forced hidden
while no anchor point exists — otherwise they would sit at their final
positions from frame 0.

Marker rules (phantom-tip guard): a marker-bearing line would render a fake
data point gliding between real samples if the tip vertex were marked, so the
tip is excluded via ``markevery``. Marker-only lines (the scatter chart is a
marker-only ``Line2D``) get no tip at all — points appear in x-order as the
sweep passes them.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from tpsplots.animation.animators.base import AlphaFade, BaseAnimator, TextFade
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.views.anim_tags import Roles

logger = logging.getLogger(__name__)


def _is_none_style(value: Any) -> bool:
    """True when a marker/linestyle spec means "draw nothing".

    Matplotlib normalizes absent markers/linestyles to the string ``'None'``;
    the documented nothing-spellings are ``'None'``, ``'none'``, ``' '``, ``''``.
    """
    return str(value).lower() in {"none", "", " "}


def _to_float(value: Any) -> float:
    """Collapse a scalar-or-length-1-array converted value to a float."""
    return float(np.asarray(value, dtype=float).reshape(-1)[0])


def _invert_easing(easing: Any, u: float) -> float:
    """Smallest ``s`` in [0, 1] with ``easing(s) >= u``.

    Used to convert a sweep-front *position* fraction into the normalized
    *time* when the front reaches it. A coarse scan brackets the first
    crossing (robust to overshoot easings that are briefly non-monotone),
    then bisection refines it.
    """
    if u <= 0.0:
        return 0.0
    lo, hi = None, None
    steps = 64
    prev = 0.0
    for k in range(1, steps + 1):
        s = k / steps
        if easing(s) >= u:
            lo, hi = prev, s
            break
        prev = s
    if hi is None:
        return 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if easing(mid) >= u:
            hi = mid
        else:
            lo = mid
    return hi


@dataclass
class _SeriesCapture:
    """Final state of one series and its tip-tracking companions."""

    line: Any
    x: np.ndarray  # converted floats; ascending when x_sorted (descending reversed)
    y: np.ndarray
    x_lo: float
    x_hi: float
    x_sorted: bool  # monotone x -> position sweep; else index-order fallback
    has_marker: bool
    marker_only: bool
    orig_markevery: Any
    anchor_final: tuple[float, float] | None = None  # where companions land
    ride_tip: bool = True  # False when the anchor sits at the sweep's origin
    label: TextFade | None = None
    label_final: tuple[float, float] | None = None
    label_offset: tuple[float, float] = (0.0, 0.0)
    endpoint: Any = None
    endpoint_fade: AlphaFade | None = None
    endpoint_final: tuple[float, float] | None = None
    endpoint_size: float = 0.0
    ring: Any = None
    ring_fade: AlphaFade | None = None
    ring_size: float = 0.0
    # Companions stay hidden until the sweep front reaches the series' first
    # finite point (a series whose data starts mid-axis has an all-NaN head).
    companion_delay: float = 0.0


class LineAnimator(BaseAnimator):
    """Animates ``line_plot`` and ``scatter_plot`` figures.

    Timeline window keys (role string first, then the global series index):
    ``("series", i)`` sweep, ``("label", i)`` label/marker fade,
    ``("pop", i)`` endpoint settle pop.
    """

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        stagger = float(self.choreo.get("stagger") or 0.0)
        draw = float(self.choreo["draw_duration"])
        sweep_easing = self.choreo_easing("easing", "quint_out")
        pop_duration = float(self.choreo["marker_pop_duration"])
        pop_easing = self.choreo_easing("marker_pop_easing", "back_out_soft")

        label_indices = {tag.index for tag, _ in self.tagged(Roles.SERIES_LABEL)}
        endpoint_indices = {tag.index for tag, _ in self.tagged(Roles.ENDPOINT)}

        for position, (tag, _) in enumerate(self.tagged(Roles.SERIES)):
            start = position * stagger
            timeline.add(("series", tag.index), Window(start, draw, sweep_easing))
            if tag.index in label_indices or tag.index in endpoint_indices:
                timeline.add(("label", tag.index), self.label_fade_window(start))
            if tag.index in endpoint_indices:
                timeline.add(("pop", tag.index), Window(start + draw, pop_duration, pop_easing))
        return timeline

    def capture(self) -> None:
        endpoints = {tag.index: artist for tag, artist in self.tagged(Roles.ENDPOINT)}
        rings = {tag.index: artist for tag, artist in self.tagged(Roles.ENDPOINT_RING)}
        labels = {tag.index: artist for tag, artist in self.tagged(Roles.SERIES_LABEL)}
        self._series: list[tuple[int, _SeriesCapture]] = []

        for tag, line in self.tagged(Roles.SERIES):
            x = np.asarray(line.get_xdata(orig=False), dtype=float)
            y = np.asarray(line.get_ydata(orig=False), dtype=float)
            finite_x = x[np.isfinite(x)]
            if finite_x.size == 0:
                continue  # nothing to reveal; leave the series static

            deltas = np.diff(finite_x)
            x_sorted = bool(np.all(deltas >= 0))
            if not x_sorted and np.all(deltas <= 0):
                # Descending x (newest-first CSVs): reverse once and sweep
                # normally — the reversed polyline renders identically (solid
                # lines/markers; dash phase may shift vs the static render).
                x, y = x[::-1], y[::-1]
                x_sorted = True
            if not x_sorted:
                logger.warning(
                    "Series %d has unsorted x values; revealing in data order "
                    "instead of a left-to-right sweep.",
                    tag.index,
                )

            capture = _SeriesCapture(
                line=line,
                x=x,
                y=y,
                x_lo=float(finite_x.min()),
                x_hi=float(finite_x.max()),
                x_sorted=x_sorted,
                has_marker=not _is_none_style(line.get_marker()),
                marker_only=_is_none_style(line.get_linestyle()),
                orig_markevery=line.get_markevery(),
            )

            endpoint = endpoints.get(tag.index)
            if endpoint is not None:
                ex = _to_float(endpoint.get_xdata(orig=False))
                ey = _to_float(endpoint.get_ydata(orig=False))
                capture.endpoint = endpoint
                capture.endpoint_fade = AlphaFade.capture(endpoint)
                capture.endpoint_final = (ex, ey)
                capture.endpoint_size = float(endpoint.get_markersize())

            ring = rings.get(tag.index)
            if ring is not None:
                capture.ring = ring
                capture.ring_fade = AlphaFade.capture(ring)
                capture.ring_size = float(ring.get_markersize())

            # Delay the companion fade until the sweep front reaches the first
            # finite point: y-NaN heads (a series that begins mid-axis) must
            # not show their label/endpoint at the final position from frame 0.
            finite_xy = np.nonzero(np.isfinite(x) & np.isfinite(y))[0]
            window = self.timeline.window(("series", tag.index))
            if finite_xy.size == 0:
                capture.companion_delay = math.inf
            elif window is not None:
                if capture.x_sorted and capture.x_hi > capture.x_lo:
                    u = (float(x[finite_xy[0]]) - capture.x_lo) / (capture.x_hi - capture.x_lo)
                else:
                    u = finite_xy[0] / len(x)
                capture.companion_delay = window.duration * _invert_easing(window.easing, u)

            capture.anchor_final = capture.endpoint_final or self._last_finite_point(x, y)
            # Ride the tip only when the anchor sits in the destination half of
            # the sweep; an origin-side anchor (descending data's data-order
            # endpoint is the LEFTMOST point) would be dragged away and snap
            # back — pin it at the final position instead.
            if capture.anchor_final is not None and capture.x_hi > capture.x_lo:
                capture.ride_tip = capture.anchor_final[0] >= 0.5 * (capture.x_lo + capture.x_hi)

            label = labels.get(tag.index)
            if label is not None:
                raw_x, raw_y = label.get_position()
                axes = label.axes
                label_final = (
                    _to_float(axes.xaxis.convert_units(raw_x)),
                    _to_float(axes.yaxis.convert_units(raw_y)),
                )
                capture.label = TextFade.capture(label)
                capture.label_final = label_final
                if capture.anchor_final is not None:
                    capture.label_offset = (
                        label_final[0] - capture.anchor_final[0],
                        label_final[1] - capture.anchor_final[1],
                    )

            self._series.append((tag.index, capture))

    def apply(self, t: float) -> None:
        for index, capture in self._series:
            progress = self.timeline.progress(("series", index), t)
            xs, ys, tip, n_real = self._reveal(capture, progress)

            if tip is not None:
                xs, ys = np.append(xs, tip[0]), np.append(ys, tip[1])
            capture.line.set_data(xs, ys)
            if capture.has_marker:
                # Exclude the interpolated tip vertex — a marked tip reads as a
                # fake data point gliding between real samples.
                capture.line.set_markevery(
                    slice(0, n_real) if tip is not None else capture.orig_markevery
                )

            if progress >= 1.0 or not capture.ride_tip:
                anchor = capture.anchor_final
            elif tip is not None:
                anchor = tip
            else:
                anchor = self._last_finite_point(xs, ys)
            self._apply_companions(capture, index, progress, anchor, t)

    # ── internals ────────────────────────────────────────────────────

    def _reveal(
        self, capture: _SeriesCapture, progress: float
    ) -> tuple[np.ndarray, np.ndarray, tuple[float, float] | None, int]:
        """Return ``(xs, ys, tip, n_real)`` for eased sweep ``progress``.

        The visible prefix runs through the last point whose x is behind the
        sweep front (requires ascending x; unsorted series reveal by index
        fraction instead). Interior NaN rows stay in the prefix — they render
        as the gap they are. The tip is interpolated only for marker-less
        lines and only when both boundary neighbors are finite: a reveal
        jumps NaN gaps rather than drawing into them.
        """
        if progress <= 0.0:
            return capture.x[:0], capture.y[:0], None, 0
        if progress >= 1.0:
            return capture.x, capture.y, None, len(capture.x)

        if capture.x_sorted:
            x_rev = capture.x_lo + progress * (capture.x_hi - capture.x_lo)
            behind = np.nonzero(capture.x <= x_rev)[0]  # NaN compares False
            if behind.size == 0:
                return capture.x[:0], capture.y[:0], None, 0
            n_real = int(behind[-1]) + 1
        else:
            x_rev = None
            n_real = max(1, math.ceil(progress * len(capture.x)))
        xs, ys = capture.x[:n_real], capture.y[:n_real]

        tip = None
        if x_rev is not None and not capture.marker_only and n_real < len(capture.x):
            x0, y0 = capture.x[n_real - 1], capture.y[n_real - 1]
            x1, y1 = capture.x[n_real], capture.y[n_real]
            if (
                x1 > x0
                and math.isfinite(x0)
                and math.isfinite(y0)
                and math.isfinite(x1)
                and math.isfinite(y1)
            ):
                fraction = (x_rev - x0) / (x1 - x0)
                tip = (x_rev, float(y0 + fraction * (y1 - y0)))
        return xs, ys, tip, n_real

    def _apply_companions(
        self,
        capture: _SeriesCapture,
        index: int,
        progress: float,
        anchor: tuple[float, float] | None,
        t: float,
    ) -> None:
        """Drive the tip-tracking label, endpoint marker, and orbit ring."""
        if capture.label is None and capture.endpoint is None and capture.ring is None:
            return

        # The fade clock is shifted by companion_delay so a series whose data
        # starts mid-axis fades its companions in when the sweep front reaches
        # its first finite point, not at the sweep start. The anchor guard
        # keeps them hidden while there is no revealed point to sit on.
        fade = self.timeline.progress(("label", index), t - capture.companion_delay)
        if anchor is None and progress < 1.0:
            fade = 0.0

        if capture.label is not None:
            if progress >= 1.0 and capture.label_final is not None:
                # Exact landing (not anchor + offset): bitwise convergence onto
                # the collision-adjusted position from the full render.
                capture.label.text.set_position(capture.label_final)
            elif anchor is not None:
                capture.label.text.set_position(
                    (anchor[0] + capture.label_offset[0], anchor[1] + capture.label_offset[1])
                )
            capture.label.apply(fade)

        if capture.endpoint is not None or capture.ring is not None:
            pop = self.timeline.progress(("pop", index), t)
            scale_from = float(self.choreo["marker_pop_scale_from"])
            pop_scale = scale_from + (1.0 - scale_from) * pop

        if capture.endpoint is not None:
            if anchor is not None:
                capture.endpoint.set_data([anchor[0]], [anchor[1]])
            capture.endpoint_fade.apply(fade)
            capture.endpoint.set_markersize(capture.endpoint_size * pop_scale)

        if capture.ring is not None:
            if anchor is not None:
                capture.ring.set_data([anchor[0]], [anchor[1]])
            capture.ring_fade.apply(fade)
            capture.ring.set_markersize(capture.ring_size * pop_scale)

    @staticmethod
    def _last_finite_point(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float] | None:
        finite = np.nonzero(np.isfinite(xs) & np.isfinite(ys))[0]
        if finite.size == 0:
            return None
        j = int(finite[-1])
        return float(xs[j]), float(ys[j])
