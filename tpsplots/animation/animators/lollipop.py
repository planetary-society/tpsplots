"""LollipopAnimator: stems grow start->end, then end markers pop in.

Each category animates in three overlapping beats on a per-category stagger:
the stem line grows from its start coordinate to its end coordinate, then the
end marker pops in (alpha fade + a size pop), and the value labels fade in — all
timed off the stem's completion. The start marker is untagged and stays static
and fully visible the whole time.

Geometry (stem length, marker size) is recomputed as ``state = f(t)`` from the
captured final state, so ``apply`` is idempotent. The end-pop uses an overshoot
easing for a subtle "settle" — that overshoot only ever scales marker size
(clamped non-negative); alpha goes through :class:`AlphaFade`, which clamps into
``[0, 1]`` so ``set_alpha`` never raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from tpsplots.animation.animators.base import AlphaFade, BaseAnimator, TextFade
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.views.anim_tags import Roles


@dataclass
class _StemCapture:
    """Final geometry of one stem line and which axis it grows along.

    Stems are always 2-point lines (the view draws ``[start, end]``), so the
    full geometry is (base, end, const) — no captured arrays needed.
    """

    line: Any
    axis: str  # "x" -> x grows start->end (y constant); "y" -> vice versa
    base: float  # varying coordinate at the start (growth origin)
    end: float  # varying coordinate at the end
    const: float  # the fixed coordinate (category position)


@dataclass
class _EndMarkerCapture:
    """Final state of one end marker (a scatter PathCollection)."""

    collection: Any
    fade: AlphaFade
    final_sizes: np.ndarray  # points**2 (area)


class LollipopAnimator(BaseAnimator):
    """Animates a ``lollipop_plot``."""

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        stagger = float(self.choreo.get("stagger") or 0.0)
        stem_duration = float(self.choreo["stem_duration"])
        stem_easing = self.choreo_easing("stem_easing", "quint_out")
        pop_duration = float(self.choreo["end_pop_duration"])
        pop_easing = self.choreo_easing("end_pop_easing", "back_out_soft")

        label_indices = {tag.index for tag, _ in self.tagged(Roles.VALUE_LABEL)}
        for tag, _ in self.tagged(Roles.STEM):
            i = tag.index
            start = i * stagger
            stem_end = start + stem_duration
            timeline.add(("stem", i), Window(start, stem_duration, stem_easing))
            timeline.add(("pop", i), Window(stem_end, pop_duration, pop_easing))
            if i in label_indices:
                timeline.add(("label", i), self.label_fade_window(stem_end))
        return timeline

    def capture(self) -> None:
        self._stems: list[tuple[int, _StemCapture]] = []
        for tag, line in self.tagged(Roles.STEM):
            x = np.asarray(line.get_xdata(orig=False), dtype=float)
            y = np.asarray(line.get_ydata(orig=False), dtype=float)
            # The stem runs along one axis while the other stays constant.
            if x[0] != x[-1]:
                axis, base, end, const = "x", float(x[0]), float(x[-1]), float(y[0])
            else:
                axis, base, end, const = "y", float(y[0]), float(y[-1]), float(x[0])
            self._stems.append((tag.index, _StemCapture(line, axis, base, end, const)))

        self._end_markers: list[tuple[int, _EndMarkerCapture]] = []
        for tag, coll in self.tagged(Roles.END_MARKER):
            self._end_markers.append(
                (
                    tag.index,
                    _EndMarkerCapture(
                        coll, AlphaFade.capture(coll), np.array(coll.get_sizes(), dtype=float)
                    ),
                )
            )

        self._labels: list[tuple[int, TextFade]] = [
            (tag.index, TextFade.capture(text)) for tag, text in self.tagged(Roles.VALUE_LABEL)
        ]

    def apply(self, t: float) -> None:
        for i, cap in self._stems:
            p = self.timeline.progress(("stem", i), t)
            # Exact FP landing at completion (base + 1.0*(end-base) is not
            # bitwise `end`); Window.progress clamps below, so p*(end-base)
            # handles the p == 0 origin exactly too.
            cur = cap.end if p >= 1.0 else cap.base + p * (cap.end - cap.base)
            if cap.axis == "x":
                cap.line.set_data([cap.base, cur], [cap.const, cap.const])
            else:
                cap.line.set_data([cap.const, cap.const], [cap.base, cur])

        for i, cap in self._end_markers:
            pop_q = self.timeline.progress(("pop", i), t)
            cap.fade.apply(pop_q)  # clamps internally; overshoot never hits alpha
            # Sizes are points**2 (area); scale by pop_q**2 for a linear-feeling
            # pop. Overshoot may exceed final (fine); never let it go negative.
            cap.collection.set_sizes(cap.final_sizes * max(pop_q, 0.0) ** 2)

        for i, fade in self._labels:
            fade.apply(self.timeline.progress(("label", i), t))
