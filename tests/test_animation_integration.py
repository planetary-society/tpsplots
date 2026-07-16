"""End-to-end animation encode test (marker: ``ffmpeg``).

This is the only animation test that actually shells out to ffmpeg and encodes
frames, so it is:

* marked ``ffmpeg`` — deselected by the default ``addopts`` (``-m 'not
  integration and not ffmpeg'``); run it with ``pytest -m ffmpeg``;
* additionally self-skipping (inside the fixture, so default runs pay no
  collection-time ffmpeg probe) when no binary is resolvable.

It is kept deliberately tiny (3 data points, draft quality, ~0.6s of video) to
stay fast.
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from tpsplots.animation.encoder import FFmpegUnavailableError, resolve_ffmpeg
from tpsplots.animation.renderer import animate_yaml

pytestmark = pytest.mark.ffmpeg


@pytest.fixture(scope="module")
def encoded_line(tmp_path_factory) -> tuple[list[Path], Path]:
    """Encode a tiny line chart once; both tests below share the output.

    Self-skips when no ffmpeg binary is resolvable — checked here rather than
    at collection time so default (deselected) runs never probe for ffmpeg.
    """
    try:
        resolve_ffmpeg()
    except FFmpegUnavailableError:
        pytest.skip("no ffmpeg binary available")

    outdir = tmp_path_factory.mktemp("animate")
    csv = outdir / "data.csv"
    csv.write_text("Year,Value\n2020,10\n2021,20\n2022,30\n", encoding="utf-8")
    yaml_path = outdir / "anim_line.yaml"
    yaml_path.write_text(
        textwrap.dedent(
            f"""
            data:
              source: csv:{csv}
            chart:
              type: line
              output: anim_line
              title: "Anim Line"
              x: "{{{{Year}}}}"
              y: "{{{{Value}}}}"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    outputs = animate_yaml(
        yaml_path,
        outdir=outdir,
        fps=10,
        duration=0.5,
        intro_hold=0.0,
        end_hold=0.1,
        quality="draft",
    )
    return outputs, outdir


def test_encode_produces_mp4_and_poster(encoded_line):
    """The encode yields a non-empty square MP4 plus a poster PNG."""
    outputs, outdir = encoded_line
    mp4 = outdir / "anim_line_square.mp4"
    poster = outdir / "anim_line_square_poster.png"

    assert mp4 in outputs
    assert poster in outputs
    assert mp4.exists() and mp4.stat().st_size > 0
    assert poster.exists() and poster.stat().st_size > 0


def test_encode_dimensions_are_1080_square(encoded_line):
    """The square MP4 is exactly 1080x1080 (probed via the bundled ffmpeg)."""
    _outputs, outdir = encoded_line
    mp4 = outdir / "anim_line_square.mp4"

    ffmpeg = resolve_ffmpeg()
    # `ffmpeg -i <file>` with no output prints stream info to stderr and exits
    # non-zero; the resolution token is stable across ffmpeg versions.
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(mp4)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "1080x1080" in proc.stderr
