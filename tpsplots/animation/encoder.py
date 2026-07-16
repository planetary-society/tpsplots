"""ffmpeg discovery and MP4 encoding for ``tpsplots animate``.

This module must stay cheap to import: ``matplotlib.animation`` and
``imageio_ffmpeg`` are imported lazily *inside* functions, never at module load
(an import-order regression test asserts neither leaks into ``sys.modules`` when
``tpsplots.views`` is imported, and the renderer imports this module).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tpsplots.exceptions import RenderingError


class FFmpegUnavailableError(RenderingError):
    """Raised when no usable ffmpeg binary can be found."""


def resolve_ffmpeg() -> str:
    """Locate an ffmpeg binary, preferring a bundled one, and return its path.

    Resolution order:

    1. ``imageio_ffmpeg.get_ffmpeg_exe()`` — honors ``IMAGEIO_FFMPEG_EXE`` and
       returns the wheel-bundled binary; raises ``RuntimeError`` if imageio is
       installed but has no usable binary. On success the path is written to
       ``matplotlib.rcParams["animation.ffmpeg_path"]`` so ``FFMpegWriter`` uses
       it.
    2. A system ffmpeg already visible to matplotlib
       (``FFMpegWriter.isAvailable()``).
    3. Otherwise :class:`FFmpegUnavailableError` with install hints.

    Raises:
        FFmpegUnavailableError: If no ffmpeg binary can be found.
    """
    import matplotlib

    try:
        import imageio_ffmpeg

        path = imageio_ffmpeg.get_ffmpeg_exe()
        matplotlib.rcParams["animation.ffmpeg_path"] = path
        return path
    except (ImportError, RuntimeError):
        # imageio-ffmpeg not installed, or installed with no usable binary.
        pass

    from matplotlib.animation import FFMpegWriter

    if FFMpegWriter.isAvailable():
        return matplotlib.rcParams["animation.ffmpeg_path"] or "ffmpeg"

    raise FFmpegUnavailableError(
        "ffmpeg is required to encode animations but was not found. Install it with:\n"
        "  pip install 'tpsplots[animate]'   (bundles a private ffmpeg binary)\n"
        "  brew install ffmpeg               (system ffmpeg, e.g. on macOS)"
    )


# CRF/preset per quality preset. draft trades size/quality for encode speed.
QUALITY_ARGS: dict[str, list[str]] = {
    "high": ["-crf", "18", "-preset", "slow"],
    "draft": ["-crf", "28", "-preset", "veryfast"],
}

# BT.709 tagging: an untagged RGB->YUV conversion lets swscale default to
# BT.601, producing a visible hue shift on brand colors (Neptune Blue / Rocket
# Flame) that Instagram then re-encodes on top of. Tagging every encode as
# BT.709 (+faststart for progressive web playback) keeps colors honest.
BT709_ARGS: list[str] = [
    "-vf",
    "scale=out_color_matrix=bt709:out_range=tv",
    "-pix_fmt",
    "yuv420p",
    # Full VUI tagging must go through x264 itself: with the bundled ffmpeg the
    # generic -colorspace/-color_primaries/-color_trc codec flags only tag the
    # matrix (primaries/transfer stay "unknown"); x264-params tags all three
    # (probe-verified: yuv420p(tv, bt709, progressive)).
    "-x264-params",
    "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv",
    "-movflags",
    "+faststart",
    "-profile:v",
    "high",
    "-level",
    "4.2",
]


def write_mp4(
    fig,
    animator,
    out_path: Path,
    *,
    fps: int,
    quality: str = "high",
    on_frame: Callable[[int, int], None] | None = None,
) -> Path:
    """Encode ``animator`` on ``fig`` to an MP4 at ``out_path``.

    Args:
        fig: The fully-rendered figure being animated (never resized here —
            ``grab_frame`` re-asserts the figure size every frame).
        animator: A prepared :class:`~tpsplots.animation.animators.base.BaseAnimator`;
            ``apply_global(t)`` sets the whole scene to wall-clock time ``t``.
        out_path: Destination ``.mp4`` path; parent dirs are created.
        fps: Output frame rate.
        quality: Key into :data:`QUALITY_ARGS` (``"high"`` or ``"draft"``).
        on_frame: Optional progress callback ``(current, total)`` per frame.

    Returns:
        ``out_path``.
    """
    # Lazy import: keeps the animation package free of matplotlib.animation at
    # import time (guarded by an import-order test).
    from matplotlib.animation import FFMpegWriter

    # matplotlib raises FileNotFoundError from saving() if the dir is missing.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Use the DEFAULT codec ("h264") — do NOT pass codec="libx264". matplotlib's
    # automatic even-dimension correction only runs when codec == "h264", and it
    # maps to libx264 anyway; naming libx264 explicitly disables that safety net.
    writer = FFMpegWriter(fps=fps, extra_args=[*BT709_ARGS, *QUALITY_ARGS[quality]])

    # Inclusive endpoint: a frame at t=0 AND one at t~=total_duration. A last
    # frame up to half a frame past the end is harmless — apply_global clamps
    # to the draw duration, so it renders the exact final state.
    total = round(animator.total_duration * fps)
    with writer.saving(fig, str(out_path), dpi=fig.dpi):
        for i in range(total + 1):
            animator.apply_global(i / fps)
            writer.grab_frame()
            if on_frame is not None:
                on_frame(i + 1, total + 1)

    return out_path
