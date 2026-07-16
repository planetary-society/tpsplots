"""Orchestrates ``tpsplots animate``: config -> figure -> animator -> MP4.

``animate_yaml`` ties the pieces together for one YAML file: it validates the
config, rejects non-animatable chart types *before* any data fetch, resolves the
animation settings, then per requested video format builds a fully-rendered
figure with the matching ``video_*`` device style, drives it through its
animator, and encodes an MP4 plus a poster PNG of the final frame.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

import matplotlib.pyplot as plt

from tpsplots.animation.animators import get_animator
from tpsplots.animation.config import CHOREOGRAPHY, resolve_animation
from tpsplots.animation.encoder import resolve_ffmpeg, write_mp4
from tpsplots.models.chart_config import chart_type_v1 as to_v1
from tpsplots.processors.yaml_chart_processor import YAMLChartProcessor

logger = logging.getLogger(__name__)


def animate_yaml(
    yaml_path: Path,
    outdir: Path = Path("charts"),
    on_frame: Callable[[int, int], None] | None = None,
    **cli_overrides,
) -> list[Path]:
    """Render animated MP4(s) for one YAML chart config.

    Args:
        yaml_path: Path to the YAML chart configuration.
        outdir: Directory for the ``.mp4`` and ``_poster.png`` outputs.
        on_frame: Optional per-frame progress callback ``(current, total)``.
            Contract (load-bearing for progress UIs): ``current`` restarts at 1
            for each requested format's encode, steps by one per frame, and the
            final call of each encode has ``current == total``.
        **cli_overrides: Animation overrides (``fps``, ``duration``, ``stagger``,
            ``easing``, ``intro_hold``, ``end_hold``, ``quality``, ``scale``);
            ``None`` values are ignored so YAML settings survive unset flags.

    Returns:
        Every output path created, ``{output}_{fmt}.mp4`` followed by
        ``{output}_{fmt}_poster.png`` for each requested format.

    Raises:
        FFmpegUnavailableError: If no ffmpeg binary is available.
        UnsupportedChartAnimation: If the chart type has no animator (raised
            before any data source is fetched).
    """
    processor = YAMLChartProcessor(yaml_path, outdir=outdir)

    # Reject non-animatable types first (a permanent config error) — before
    # the fixable environment check and long before any data fetch.
    chart_type_v1 = to_v1(processor.config.chart.type)
    animator_cls = get_animator(chart_type_v1)  # raises UnsupportedChartAnimation

    # Fail fast with a friendly install hint for library users (the CLI also
    # calls this up front). Cheap and side-effect-free beyond setting rcParams.
    resolve_ffmpeg()

    anim = resolve_animation(processor.config.animation, **cli_overrides)

    ctx, view = processor.prepare_render()

    # A YAML figsize/dpi would break the exact video pixel dimensions that the
    # device styles guarantee — strip once (format-independent), with a warning.
    base_params = deepcopy(ctx.resolved_params)
    for key in ("figsize", "dpi"):
        if base_params.pop(key, None) is not None:
            logger.warning(
                "Ignoring YAML %r for animated output %r — video dimensions are "
                "fixed by the video device styles.",
                key,
                ctx.output_name,
            )

    # draft quality forces <=30fps regardless of the resolved fps.
    fps = anim.fps if anim.quality != "draft" else min(anim.fps, 30)

    outputs: list[Path] = []
    for fmt in anim.formats:
        params = deepcopy(base_params)
        device = f"video_{fmt}"
        style = view.device_style(device)
        style_dpi = style["dpi"]
        if anim.scale != 1:
            # Super-sample the encode (e.g. --scale 2 landscape -> 3840x2160).
            params["dpi"] = style_dpi * anim.scale

        # Compute expected pixels FROM the style dict — single source of truth,
        # no duplicated pixel table.
        expected_px = tuple(round(dim * style_dpi * anim.scale) for dim in style["figsize"])

        fig = view.create_figure(metadata=deepcopy(ctx.resolved_metadata), device=device, **params)
        try:
            animator = animator_cls(fig, anim, CHOREOGRAPHY[chart_type_v1], expected_px=expected_px)
            animator.prepare()

            mp4_path = outdir / f"{ctx.output_name}_{fmt}.mp4"
            write_mp4(fig, animator, mp4_path, fps=fps, quality=anim.quality, on_frame=on_frame)

            # Restore the exact final state, then save it as the poster frame.
            animator.finalize()
            poster_path = outdir / f"{ctx.output_name}_{fmt}_poster.png"
            fig.savefig(poster_path)

            outputs.extend((mp4_path, poster_path))
        finally:
            plt.close(fig)

    return outputs
