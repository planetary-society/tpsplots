"""AreaAnimator: truthful left-to-right collection clipping."""

from dataclasses import dataclass
from typing import Any

from matplotlib.transforms import Bbox

from tpsplots.animation.animators.base import BaseAnimator
from tpsplots.animation.timeline import Timeline, Window
from tpsplots.views.anim_tags import Roles


@dataclass(frozen=True, slots=True)
class _AreaCapture:
    """Exact final clipping state for one rendered area collection."""

    collection: Any
    clip_on: bool
    clip_box: Any
    clip_path: Any


class AreaAnimator(BaseAnimator):
    """Reveal all area layers through one shared axes-space sweep frontier."""

    _WINDOW_KEY = ("area", 0)

    def build_timeline(self) -> Timeline:
        timeline = Timeline()
        timeline.add(
            self._WINDOW_KEY,
            Window(
                0.0,
                float(self.choreo["draw_duration"]),
                self.choreo_easing("easing", "cubic_in_out"),
            ),
        )
        return timeline

    def capture(self) -> None:
        self._areas = [
            _AreaCapture(
                collection=collection,
                clip_on=collection.get_clip_on(),
                clip_box=collection.get_clip_box(),
                clip_path=collection.get_clip_path(),
            )
            for _tag, collection in self.tagged(Roles.SERIES)
        ]

    @staticmethod
    def _restore(capture: _AreaCapture) -> None:
        capture.collection.set_clip_on(capture.clip_on)
        capture.collection.set_clip_box(capture.clip_box)
        capture.collection.set_clip_path(capture.clip_path)

    def apply(self, t: float) -> None:
        progress = self.clamp01(self.timeline.progress(self._WINDOW_KEY, t))
        if progress >= 1.0:
            for capture in self._areas:
                self._restore(capture)
            return

        for capture in self._areas:
            collection = capture.collection
            axes_box = Bbox.from_extents(0.0, 0.0, progress, 1.0).transformed(
                collection.axes.transAxes
            )
            clip_box = axes_box
            if capture.clip_box is not None:
                intersection = Bbox.intersection(axes_box, capture.clip_box)
                if intersection is not None:
                    clip_box = intersection
                else:
                    clip_box = Bbox.from_extents(axes_box.x0, axes_box.y0, axes_box.x0, axes_box.y1)
            collection.set_clip_on(True)
            collection.set_clip_box(clip_box)
