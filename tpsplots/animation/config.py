"""Single source of animation defaults, choreography constants, and resolution.

This module is deliberately dependency-light (no matplotlib, no pydantic import
at module load) so :mod:`tpsplots.animation` stays cheap to import.

Precedence for the ``tpsplots animate`` pipeline is **CLI > YAML > defaults**.
To make that distinction possible, the YAML-facing model
(:class:`tpsplots.models.animation.AnimationConfig`) leaves every field ``None``
when unset, and the concrete fallback values live here in :data:`DEFAULTS` — the
ONLY place they are defined, so the two can never drift.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# The one and only place concrete animation defaults live. A field left as
# ``None`` here means "let the per-chart-type choreography decide" (see
# CHOREOGRAPHY below) rather than "no value".
DEFAULTS: dict[str, Any] = {
    "formats": ("square",),
    "fps": 60,
    "duration": None,  # None -> per-chart-type draw_duration from CHOREOGRAPHY
    "stagger": None,  # None -> per-chart-type stagger from CHOREOGRAPHY
    "easing": None,  # None -> per-chart-type easing from CHOREOGRAPHY
    "intro_hold": 0,  # still frames (chrome fully visible) before the data draws
    "end_hold": 2.0,
    "quality": "high",
}

# Format aliases expandable from the CLI ``--format all`` flag.
_ALL_FORMATS = ("square", "landscape", "portrait")


@dataclass(frozen=True)
class ResolvedAnimation:
    """Fully-resolved animation settings after merging defaults, YAML, and CLI.

    Field names mirror :data:`DEFAULTS` keys, with ``formats`` normalized to a
    tuple. ``scale`` is CLI-only (super-sampling factor for high-res encodes)
    and has no YAML surface.
    """

    formats: tuple[str, ...]
    fps: int
    duration: float | None
    stagger: float | None
    easing: str | None
    intro_hold: float
    end_hold: float
    quality: str
    scale: int = 1


def _normalize_formats(formats: Any) -> tuple[str, ...]:
    """Coerce a formats value to a validated, deduped tuple.

    Expands the ``"all"`` alias and rejects unknown format names — YAML formats
    are Literal-validated by Pydantic, but CLI/library callers funnel arbitrary
    strings through here, and this is the one chokepoint that owns the format
    vocabulary.

    Raises:
        ValueError: If a format is not one of ``_ALL_FORMATS`` or ``"all"``.
    """
    if isinstance(formats, str):
        formats = (formats,)
    expanded: list[str] = []
    for fmt in formats:
        if fmt != "all" and fmt not in _ALL_FORMATS:
            valid = ", ".join((*_ALL_FORMATS, "all"))
            raise ValueError(f"Unknown video format {fmt!r}. Valid formats: {valid}.")
        for resolved in _ALL_FORMATS if fmt == "all" else (fmt,):
            if resolved not in expanded:
                expanded.append(resolved)
    return tuple(expanded)


def resolve_animation(yaml_cfg: Any = None, **cli_overrides: Any) -> ResolvedAnimation:
    """Merge DEFAULTS <- YAML <- CLI into a :class:`ResolvedAnimation`.

    Args:
        yaml_cfg: An ``AnimationConfig`` (or any object exposing ``model_dump``,
            or a plain mapping) from the parsed YAML, or ``None``. Only its
            non-``None`` fields override the defaults.
        **cli_overrides: CLI flag values keyed by DEFAULTS field name plus the
            CLI-only ``scale``. A value of ``None`` means "flag not passed" and
            does NOT override — this is the precedence-bug guard that lets a
            YAML value survive when the corresponding CLI flag is absent.

    Returns:
        The fully-resolved settings.

    Raises:
        TypeError: If a non-``None`` ``cli_overrides`` key is not a recognized
            field (raised by the ``ResolvedAnimation`` constructor).
    """
    resolved: dict[str, Any] = dict(DEFAULTS)
    resolved["scale"] = 1

    # Overlay YAML (non-None only).
    if yaml_cfg is not None:
        if hasattr(yaml_cfg, "model_dump"):
            yaml_data: Mapping[str, Any] = yaml_cfg.model_dump(exclude_none=True)
        else:
            yaml_data = dict(yaml_cfg)
        for key, value in yaml_data.items():
            if value is not None and key in DEFAULTS:
                resolved[key] = value

    # Overlay CLI (non-None only) — None means "flag not passed".
    for key, value in cli_overrides.items():
        if value is not None:
            resolved[key] = value

    resolved["formats"] = _normalize_formats(resolved["formats"])
    return ResolvedAnimation(**resolved)


# User override -> choreography key folding for effective_choreography(). An
# override applies only when the chart type's choreography defines the target
# key (e.g. `stagger` is ignored for grouped/stacked bars, which have no
# single stagger knob). Keep in lockstep with the CHOREOGRAPHY key names.
_OVERRIDE_KEYS = (
    ("duration", "draw_duration"),
    ("stagger", "stagger"),
    ("easing", "easing"),
)


def effective_choreography(choreo: Mapping[str, Any], anim: ResolvedAnimation) -> dict[str, Any]:
    """Fold a user's duration/stagger/easing overrides into per-type constants."""
    effective = dict(choreo)
    for override_key, choreo_key in _OVERRIDE_KEYS:
        value = getattr(anim, override_key)
        if value is not None and choreo_key in effective:
            effective[choreo_key] = value
    return effective


# ---------------------------------------------------------------------------
# Choreography: the single tuning surface for motion design.
#
# Per-chart-type constants keyed by chart_type_v1. Animators read these to size
# each phase; tweaking the feel of the motion means editing values here, not the
# animator code. Easings are stored as NAME STRINGS (resolved via
# tpsplots.animation.easing.get_easing) so this module stays matplotlib-free.
# ---------------------------------------------------------------------------
# Lines/scatter: animate all series simultaneously by default (staggered tips
# read as render lag); the sweep uses cubic_in_out — a slow anticipation, a
# rush through the middle, and a decelerating seat (the news-graphics glide).
# Tip labels fade in; the endpoint marker gets a small settle pop at landing.
# Scatter aliases line — one tuning surface.
_LINE_CHOREO: dict[str, Any] = {
    "draw_duration": 3.0,
    "stagger": 0.0,  # simultaneous series by default; opt-in >= 0.6s
    "easing": "cubic_in_out",  # sweep easing
    "label_fade": 0.1,  # tip label fade-in
    "label_fade_easing": "cubic_out",
    "marker_pop_duration": 0.1,  # endpoint settle pop
    "marker_pop_easing": "back_out_soft",  # geometry only (never alpha)
    "marker_pop_scale_from": 0.85,  # marker rides the tip at this size fraction
}

CHOREOGRAPHY: dict[str, dict[str, Any]] = {
    "area_plot": {
        "draw_duration": 3.0,
        "easing": "cubic_in_out",
    },
    "line_plot": _LINE_CHOREO,
    "scatter_plot": _LINE_CHOREO,
    # Bars: cubic_in_out (honest values on paused frames; overshoot opt-in).
    # Small n gets a visible cascade; large n collapses to a fast wave.
    "bar_plot": {
        "draw_duration": 2.0,
        "bar_duration": 0.45,
        "stagger_min_frac": 0.3,  # cascade span for n <= large_n_threshold
        "stagger_max_frac": 0.5,
        "wave_stagger": 0.12,  # fast wave for large n
        "large_n_threshold": 10,
        "easing": "cubic_in_out",
        "label_fade": 0.3,
        "label_fade_easing": "cubic_out",
        "label_start_frac": 0.8,  # value label fades at 80% of the bar window
        "label_start_frac_overshoot": 1.0,  # ...or 100% when overshoot is active
    },
    "grouped_bar_plot": {
        "draw_duration": 2.25,
        "cluster_stagger": 0.22,
        "group_offset": 0.05,
        "bar_duration": 0.4,
        "layer1_gap": 0.05,  # pause between a stacked base landing and its top layer
        "easing": "cubic_in_out",
        "label_fade": 0.3,
        "label_fade_easing": "cubic_out",
        "label_start_frac": 0.8,
        "label_start_frac_overshoot": 1.0,
    },
    "stacked_bar_plot": {
        "layer_duration": 0.85,
        "layer_offset": 0.6,  # layer k starts at k * layer_offset (overlap)
        "easing": "cubic_in_out",
        "label_fade": 0.4,  # segment/total labels fade after the last layer
        "label_fade_easing": "cubic_out",
    },
    "lollipop_plot": {
        "stagger": 0.18,  # per-category start offset
        "stem_duration": 0.35,
        "stem_easing": "cubic_in_out",
        "end_pop_duration": 0.2,
        "end_pop_easing": "back_out_soft",  # geometry only
        "label_fade": 0.3,  # labels fade at completion
        "label_fade_easing": "cubic_out",
    },
}
