"""Bar-family animators: plain, grouped, and stacked bars.

All three grow bars from their baseline anchor by scaling the rect's *signed*
extent — matplotlib pins the rect at ``bottom``/``left`` (the baseline) and
stores a signed height/width, so ``rect.set_height(h * p)`` animates a negative
bar downward and a positive bar upward with the anchor unmoved. Every
``apply(t)`` is pure ``state = f(t)`` (idempotent): geometry is recomputed from
the captured final extents and the timeline's progress, never accumulated.

Value labels fade in (alpha only) once their bar has essentially landed; their
positions stay at the fully-rendered final coordinates. Overshoot easings may
push a bar's progress briefly above ``1.0`` — that only ever drives geometry,
so it is safe; alpha goes through :class:`TextFade`, which clamps internally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tpsplots.animation.animators.base import BaseAnimator, TextFade
from tpsplots.animation.easing import OVERSHOOT_EASINGS
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.views.anim_tags import Roles


def _label_start_frac(choreo: Any) -> float:
    """Fraction of a bar's window at which its value label begins to fade.

    Under an overshoot easing the label waits for 100% of the window — a
    paused overshoot frame would otherwise show a label over a bar that is
    still visibly past its honest value.
    """
    overshoot = choreo.get("easing") in OVERSHOOT_EASINGS
    key = "label_start_frac_overshoot" if overshoot else "label_start_frac"
    return float(choreo[key])


@dataclass
class _BarCapture:
    """Final geometry of one bar rect."""

    rect: Any
    orient: str  # "v" -> animate height; "h" -> animate width
    extent: float  # signed final height (vertical) or width (horizontal)


class BarAnimator(BaseAnimator):
    """Animates a ``bar_plot``: bars cascade in from the baseline."""

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        bars = self.tagged(Roles.BAR)
        n = len(bars)
        if n == 0:
            return timeline

        orient = bars[0][0].meta.get("orient", "v")
        bar_duration = float(self.choreo["bar_duration"])
        draw_duration = float(self.choreo["draw_duration"])
        easing = self.choreo_easing("easing", "quint_out")

        # Cascade span: a visible per-bar delay for small n (clamped to a
        # fraction of the bar duration), collapsing to a fast wave for large n.
        spread = (draw_duration - bar_duration) / max(n - 1, 1)
        if n <= int(self.choreo["large_n_threshold"]):
            stagger = min(
                max(spread, float(self.choreo["stagger_min_frac"]) * bar_duration),
                float(self.choreo["stagger_max_frac"]) * bar_duration,
            )
        else:
            stagger = min(float(self.choreo["wave_stagger"]), spread)

        # Vertical bars cascade left->right by index; horizontal bars cascade in
        # reading order top->bottom, and barh index 0 sits at the BOTTOM, so the
        # top-most (last) index starts first.
        for tag, _ in bars:
            j = tag.index
            start = (n - 1 - j) * stagger if orient == "h" else j * stagger
            timeline.add(("bar", j), Window(start, bar_duration, easing))

        label_frac = _label_start_frac(self.choreo)
        for tag, _ in self.tagged(Roles.VALUE_LABEL):
            window = timeline.window(("bar", tag.index))
            bar_start = window.start if window is not None else 0.0
            timeline.add(
                ("label", tag.index),
                self.label_fade_window(bar_start + label_frac * bar_duration),
            )
        return timeline

    def capture(self) -> None:
        self._bars: list[tuple[int, _BarCapture]] = []
        for tag, rect in self.tagged(Roles.BAR):
            orient = tag.meta.get("orient", "v")
            extent = rect.get_height() if orient == "v" else rect.get_width()
            self._bars.append((tag.index, _BarCapture(rect, orient, float(extent))))
        self._labels: dict[int, TextFade] = {
            tag.index: TextFade.capture(text) for tag, text in self.tagged(Roles.VALUE_LABEL)
        }

    def apply(self, t: float) -> None:
        for j, cap in self._bars:
            grown = cap.extent * self.timeline.progress(("bar", j), t)
            if cap.orient == "v":
                cap.rect.set_height(grown)
            else:
                cap.rect.set_width(grown)
        for j, fade in self._labels.items():
            fade.apply(self.timeline.progress(("label", j), t))


class GroupedBarAnimator(BaseAnimator):
    """Animates a ``grouped_bar_plot``: clustered bars, optional stacked tops.

    Each bar is keyed ``("bar", category, group, layer)``. Layer-0 bases cascade
    by cluster (category) and within-cluster group offset; a layer-1 stacked
    portion (only present in the mixed simple/stacked config) starts once its own
    base has landed, so it can keep its captured final anchor (the base's full
    height) and simply grow the segment on top.

    Vertical-only by design: the grouped bar view has no horizontal mode (its
    BAR tags carry no ``orient`` meta). If the view ever grows one, tag
    ``orient`` and mirror :class:`BarAnimator`'s width path.
    """

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        cluster_stagger = float(self.choreo["cluster_stagger"])
        group_offset = float(self.choreo["group_offset"])
        bar_duration = float(self.choreo["bar_duration"])
        layer1_gap = float(self.choreo["layer1_gap"])
        easing = self.choreo_easing("easing", "quint_out")

        # Track each cell's latest window start so label timing keys off the
        # cell's LAST layer without re-deriving the schedule.
        last_start_by_cell: dict[tuple[int, int], float] = {}
        for tag, _ in self.tagged(Roles.BAR):
            j = tag.index
            i = int(tag.meta["group"])
            start = j * cluster_stagger + i * group_offset
            if int(tag.meta["layer"]) > 0:
                # Start after the base (layer 0) has fully landed.
                start += bar_duration + layer1_gap
            cell = (j, i)
            last_start_by_cell[cell] = max(last_start_by_cell.get(cell, 0.0), start)
            timeline.add(("bar", j, i, int(tag.meta["layer"])), Window(start, bar_duration, easing))

        label_frac = _label_start_frac(self.choreo)
        for tag, _ in self.tagged(Roles.VALUE_LABEL):
            cell = (tag.index, int(tag.meta["group"]))
            last_start = last_start_by_cell.get(cell, 0.0)
            timeline.add(
                ("label", *cell),
                self.label_fade_window(last_start + label_frac * bar_duration),
            )
        return timeline

    def capture(self) -> None:
        self._bars: list[tuple[tuple[str, int, int, int], Any]] = []
        for tag, rect in self.tagged(Roles.BAR):
            key = ("bar", tag.index, int(tag.meta["group"]), int(tag.meta["layer"]))
            self._bars.append((key, (rect, float(rect.get_height()))))
        self._labels: dict[tuple[int, int], TextFade] = {}
        for tag, text in self.tagged(Roles.VALUE_LABEL):
            self._labels[(tag.index, int(tag.meta["group"]))] = TextFade.capture(text)

    def apply(self, t: float) -> None:
        for key, (rect, extent) in self._bars:
            rect.set_height(extent * self.timeline.progress(key, t))
        for (j, i), fade in self._labels.items():
            fade.apply(self.timeline.progress(("label", j, i), t))


class StackedBarAnimator(BaseAnimator):
    """Animates a ``stacked_bar_plot``: whole layers grow together, in order.

    Layer ``k`` is scheduled as one window (``("layer", k)``) starting at
    ``k * layer_offset``. Per frame the running stack is recomputed from the
    category's baseline upward — ``set_y``/``set_x`` to the current running
    bottom, then ``set_height``/``set_width`` to the eased segment extent —
    so segments stay perfectly seated on each other under any window overlap.
    Captured bottoms are never animated directly.
    """

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        layers = {int(tag.meta["layer"]) for tag, _ in self.tagged(Roles.BAR_SEGMENT)}
        if not layers:
            return timeline

        layer_duration = float(self.choreo["layer_duration"])
        layer_offset = float(self.choreo["layer_offset"])
        easing = self.choreo_easing("easing", "quint_out")
        for k in layers:
            timeline.add(("layer", k), Window(k * layer_offset, layer_duration, easing))

        if self.tagged(Roles.SEGMENT_LABEL) or self.tagged(Roles.STACK_LABEL):
            last_end = max(layers) * layer_offset + layer_duration
            timeline.add(("labels",), self.label_fade_window(last_end))
        return timeline

    def capture(self) -> None:
        self._orient = "v"
        grouped: dict[int, list[tuple[int, Any, float, float]]] = {}
        for tag, rect in self.tagged(Roles.BAR_SEGMENT):
            self._orient = tag.meta.get("orient", "v")
            if self._orient == "v":
                extent, bottom = float(rect.get_height()), float(rect.get_y())
            else:
                extent, bottom = float(rect.get_width()), float(rect.get_x())
            grouped.setdefault(tag.index, []).append((int(tag.meta["layer"]), rect, extent, bottom))

        # Per category: segments sorted by layer, baseline = the LOWEST existing
        # layer's captured anchor (not hardcoded layer 0 / 0.0 — stacks can sit
        # on a bottom_values offset).
        self._stacks: dict[int, list[tuple[int, Any, float]]] = {}
        self._baseline: dict[int, float] = {}
        layers: set[int] = set()
        for j, segments in grouped.items():
            segments.sort(key=lambda item: item[0])
            self._baseline[j] = segments[0][3]
            self._stacks[j] = [(k, rect, extent) for k, rect, extent, _bottom in segments]
            layers.update(k for k, *_ in segments)
        self._layer_order = sorted(layers)

        self._label_fades = [
            TextFade.capture(text)
            for _, text in (*self.tagged(Roles.SEGMENT_LABEL), *self.tagged(Roles.STACK_LABEL))
        ]

    def apply(self, t: float) -> None:
        # Layer progress depends only on the layer, not the category — compute
        # once per frame.
        progress = {k: self.timeline.progress(("layer", k), t) for k in self._layer_order}
        vertical = self._orient == "v"
        for j, segments in self._stacks.items():
            bottom = self._baseline[j]
            for k, rect, extent in segments:
                grown = extent * progress[k]
                if vertical:
                    rect.set_y(bottom)
                    rect.set_height(grown)
                else:
                    rect.set_x(bottom)
                    rect.set_width(grown)
                bottom += grown

        label_p = self.timeline.progress(("labels",), t)
        for fade in self._label_fades:
            fade.apply(label_p)
