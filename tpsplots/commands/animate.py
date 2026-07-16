"""Render animated MP4 videos of charts building themselves out.

The ``tpsplots animate`` command mirrors ``generate``'s per-file loop,
status/summary output, and exit-code conventions, but drives the animation
pipeline (:func:`tpsplots.animation.renderer.animate_yaml`) instead of static
rendering. Only the line and bar chart families are animatable in v1; other
chart types report a clear "not animatable" failure and the batch continues.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Annotated, Any

import typer

from tpsplots.animation.animators import UnsupportedChartAnimation
from tpsplots.animation.encoder import FFmpegUnavailableError, resolve_ffmpeg
from tpsplots.animation.renderer import animate_yaml
from tpsplots.exceptions import ConfigurationError, TPSPlotsError

logger = logging.getLogger(__name__)


class _EncodeProgress:
    """Lazily-created per-encode progress bar driven by ``on_frame``.

    ``animate_yaml``'s callback contract: ``current`` restarts at 1 for each
    requested video format and steps by one per frame, so a bar is opened on
    each ``current == 1`` and closed when the encode completes. Bars are
    created on the first frame because ``total`` is only known then.
    """

    def __init__(self) -> None:
        self._bar: Any = None

    def __call__(self, current: int, total: int) -> None:
        if self._bar is None or current == 1:
            self.close()
            self._bar = typer.progressbar(length=total, label="  encoding")
            self._bar.__enter__()
        self._bar.update(1)
        if current >= total:
            self.close()

    def close(self) -> None:
        if self._bar is not None:
            self._bar.__exit__(None, None, None)
            self._bar = None


def animate(
    inputs: Annotated[
        list[Path],
        typer.Argument(help="YAML configuration file(s) or directory(ies) to animate"),
    ],
    outdir: Annotated[
        Path,
        typer.Option("--outdir", "-o", help="Output directory for generated videos"),
    ] = Path("charts"),
    formats: Annotated[
        list[str] | None,
        typer.Option(
            "--format",
            "-f",
            help="Video aspect(s): square, landscape, portrait, or all (repeatable)",
        ),
    ] = None,
    fps: Annotated[
        int | None,
        typer.Option("--fps", help="Frames per second (overrides YAML/default)"),
    ] = None,
    duration: Annotated[
        float | None,
        typer.Option("--duration", help="Draw-phase length in seconds"),
    ] = None,
    end_hold: Annotated[
        float | None,
        typer.Option("--end-hold", help="Seconds to hold on the final frame"),
    ] = None,
    quality: Annotated[
        str | None,
        typer.Option("--quality", help="Encode quality: high or draft (draft caps fps at 30)"),
    ] = None,
    scale: Annotated[
        int | None,
        typer.Option(
            "--scale",
            help="Super-sample factor for higher-res encodes (e.g. 2 -> 4K landscape)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output (errors still shown)"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable verbose/debug logging"),
    ] = False,
) -> None:
    """Render animated MP4 videos of charts drawing themselves out.

    Animatable chart types (v1): line, scatter, bar, grouped_bar, stacked_bar,
    lollipop. Each produces ``{output}_{format}.mp4`` plus a poster PNG of the
    final frame. Override flags left unset fall back to the YAML ``animation:``
    block, then to built-in defaults.

    Exit codes (matching ``generate``):

        0  All charts animated successfully.

        1  One or more charts failed (render errors or non-animatable types).

        2  Environment, usage, or config errors (no ffmpeg binary, no YAML
           files found, invalid YAML configuration).

    Examples:

        tpsplots animate yaml/chart.yaml                Animate a single chart (square)

        tpsplots animate yaml/                          Animate all YAML in a directory

        tpsplots animate --format all yaml/chart.yaml   Square, landscape, and portrait

        tpsplots animate --scale 2 --format landscape chart.yaml   4K landscape for YouTube
    """
    # Lazy import: cli.py imports this module at load time, so importing these
    # from tpsplots.cli at module scope would be a circular import.
    from tpsplots.cli import (
        collect_yaml_files,
        emit_generate_status,
        emit_generate_summary,
        setup_logging,
    )

    setup_logging(verbose=verbose, quiet=quiet)

    # Fail fast on a missing ffmpeg binary — an environment error (exit 2) with
    # install hints, before any files are processed.
    try:
        resolve_ffmpeg()
    except FFmpegUnavailableError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    yaml_files, input_errors = collect_yaml_files(inputs)

    if input_errors:
        for error in input_errors:
            logger.error(error)
        raise typer.Exit(code=2)

    if not yaml_files:
        logger.error("No YAML files found to process")
        raise typer.Exit(code=2)

    outdir.mkdir(parents=True, exist_ok=True)

    # Every override is None unless its flag was passed, so YAML animation
    # settings survive an unset flag (resolve_animation ignores None values).
    overrides: dict[str, Any] = {
        "formats": formats,
        "fps": fps,
        "duration": duration,
        "end_hold": end_hold,
        "quality": quality,
        "scale": scale,
    }

    total = len(yaml_files)
    if not quiet:
        typer.secho(f"Animating {total} chart(s)", fg=typer.colors.CYAN, bold=True)

    success_count = 0
    failure_count = 0
    config_error_count = 0
    failure_details: list[str] = []

    for index, yaml_file in enumerate(yaml_files, start=1):
        if not quiet:
            typer.secho(f"[{index}/{total}] {yaml_file.name}", fg=typer.colors.CYAN)

        progress = _EncodeProgress()
        try:
            outputs = animate_yaml(
                yaml_file,
                outdir=outdir,
                on_frame=None if quiet else progress,
                **overrides,
            )
        except ConfigurationError as exc:
            emit_generate_status(index, total, yaml_file.name, "fail", detail=str(exc), quiet=quiet)
            config_error_count += 1
            failure_details.append(f"{yaml_file.name}: config error - {exc}")
            if verbose:
                traceback.print_exc()
            continue
        except TPSPlotsError as exc:
            # Covers UnsupportedChartAnimation too — its message already carries
            # the "not animatable yet" framing plus the supported-types list.
            emit_generate_status(index, total, yaml_file.name, "fail", detail=str(exc), quiet=quiet)
            failure_count += 1
            failure_details.append(f"{yaml_file.name}: {exc}")
            if verbose and not isinstance(exc, UnsupportedChartAnimation):
                traceback.print_exc()
            continue
        except Exception as exc:
            emit_generate_status(
                index,
                total,
                yaml_file.name,
                "fail",
                detail=f"unexpected error: {exc}",
                quiet=quiet,
            )
            failure_count += 1
            failure_details.append(f"{yaml_file.name}: unexpected error - {exc}")
            if verbose:
                traceback.print_exc()
            continue
        finally:
            progress.close()

        success_count += 1
        emit_generate_status(index, total, yaml_file.name, "ok", quiet=quiet)
        if not quiet:
            for path in outputs:
                typer.echo(f"    {path.name}")

    emit_generate_summary(
        success_count=success_count,
        failure_count=failure_count,
        config_error_count=config_error_count,
        failure_details=failure_details,
        verbose=verbose,
        quiet=quiet,
        logger=logger,
    )

    if config_error_count > 0:
        raise typer.Exit(code=2)
    if failure_count > 0:
        raise typer.Exit(code=1)
