"""Animator registry: chart_type_v1 → animator class.

Animator modules import lazily so the registry (and its clean unsupported-type
error) is usable without pulling in every animator's dependencies.
"""

import importlib

from tpsplots.exceptions import RenderingError

# chart_type_v1 -> (module, class name). Keys are the animatable chart types;
# everything else gets UnsupportedChartAnimation.
_ANIMATOR_MODULES: dict[str, tuple[str, str]] = {
    "area_plot": ("tpsplots.animation.animators.area", "AreaAnimator"),
    "line_plot": ("tpsplots.animation.animators.line", "LineAnimator"),
    "scatter_plot": ("tpsplots.animation.animators.line", "LineAnimator"),
    "bar_plot": ("tpsplots.animation.animators.bars", "BarAnimator"),
    "grouped_bar_plot": ("tpsplots.animation.animators.bars", "GroupedBarAnimator"),
    "stacked_bar_plot": ("tpsplots.animation.animators.bars", "StackedBarAnimator"),
    "lollipop_plot": ("tpsplots.animation.animators.lollipop", "LollipopAnimator"),
}


class UnsupportedChartAnimation(RenderingError):
    """Raised when a chart type has no animator yet."""


def supported_chart_types() -> tuple[str, ...]:
    """The animatable chart_type_v1 names, sorted."""
    return tuple(sorted(_ANIMATOR_MODULES))


def get_animator(chart_type_v1: str):
    """Return the animator class for ``chart_type_v1``.

    Raises:
        UnsupportedChartAnimation: If the chart type is not animatable; the
            message lists the supported YAML type names.
    """
    entry = _ANIMATOR_MODULES.get(chart_type_v1)
    if entry is None:
        # v1 names are "<yaml type>_plot" — show the YAML-facing names.
        yaml_name = chart_type_v1.removesuffix("_plot")
        supported = ", ".join(name.removesuffix("_plot") for name in supported_chart_types())
        raise UnsupportedChartAnimation(
            f"Chart type '{yaml_name}' is not animatable yet. Animatable types: {supported}."
        )
    module_path, class_name = entry
    return getattr(importlib.import_module(module_path), class_name)
