"""Vector logo rendering from EPS for chart footers.

Parses the TPS combined logo EPS into a matplotlib compound ``Path``
and draws it as a resolution-independent ``PathPatch``.
"""

import logging
import struct

from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.transforms import Affine2D

from tpsplots import IMAGES_DIR

logger = logging.getLogger(__name__)

# ── EPS source and bounding-box constants ──────────────────────────
_EPS_FILE = IMAGES_DIR / "TPS_Logo_1Line-Black-Cutout.eps"

# HiResBoundingBox: 63.1520 0 2104.2413 193.0806
_EPS_LEFT = 63.152
_EPS_BOTTOM = 0.0
_EPS_RIGHT = 2104.2413
_EPS_HEIGHT = 193.0806
_EPS_WIDTH = _EPS_RIGHT - _EPS_LEFT  # ≈ 2041.09

_LOGO_COLOR = "#545454"

# Module-level cache — parsed once, reused across all renders.
_cached_path: MplPath | None = None


# ── EPS text extraction ────────────────────────────────────────────
def _read_eps_text(path) -> str:
    """Return the PostScript text from *path*, handling DOS binary EPS."""
    with open(path, "rb") as fh:
        magic = fh.read(4)
        if magic == b"\xc5\xd0\xd3\xc6":
            # DOS binary EPS: header has PS offset/length at bytes 4-11
            ps_offset, ps_length = struct.unpack("<II", fh.read(8))
            fh.seek(ps_offset)
            return fh.read(ps_length).decode("latin-1")
        # Plain-text EPS — rewind and read everything
        fh.seek(0)
        return fh.read().decode("latin-1")


# ── EPS → matplotlib Path ─────────────────────────────────────────
def _parse_eps_to_path(path) -> MplPath:
    """Parse the art section of *path* into a matplotlib compound ``Path``.

    Extracts lines between ``clp`` and ``false sop``, interpreting
    ``mo``/``li``/``cv``/``cp`` PostScript drawing commands.  Y coordinates
    are flipped (``y = EPS_HEIGHT - y_raw``) because the EPS applies
    ``1 -1 scale 0 -H translate`` before the art section.
    """
    text = _read_eps_text(path)
    lines = text.splitlines()

    # Locate art section markers
    start = None
    end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "clp" and start is None:
            start = i + 1
        elif "false sop" in stripped and start is not None:
            end = i
            break

    if start is None or end is None:
        raise ValueError("Could not find clp / false sop art section markers in EPS")

    vertices: list[tuple[float, float]] = []
    codes: list[int] = []

    for line in lines[start:end]:
        parts = line.strip().split()
        if not parts:
            continue
        op = parts[-1]
        nums = [float(x) for x in parts[:-1]]

        if op == "mo" and len(nums) == 2:
            vertices.append((nums[0], _EPS_HEIGHT - nums[1]))
            codes.append(MplPath.MOVETO)
        elif op == "li" and len(nums) == 2:
            vertices.append((nums[0], _EPS_HEIGHT - nums[1]))
            codes.append(MplPath.LINETO)
        elif op == "cv" and len(nums) == 6:
            for j in range(0, 6, 2):
                vertices.append((nums[j], _EPS_HEIGHT - nums[j + 1]))
                codes.append(MplPath.CURVE4)
        elif op == "cp":
            vertices.append((0.0, 0.0))
            codes.append(MplPath.CLOSEPOLY)

    if not vertices:
        raise ValueError("No path commands found in EPS art section")

    return MplPath(vertices, codes)


# ── Cached accessor ────────────────────────────────────────────────
def get_cached_path() -> MplPath | None:
    """Return the parsed logo path, loading from disk on first call."""
    global _cached_path
    if _cached_path is not None:
        return _cached_path
    if not _EPS_FILE.exists():
        return None
    _cached_path = _parse_eps_to_path(_EPS_FILE)
    return _cached_path


# ── Draw into a figure ─────────────────────────────────────────────
def draw_logo(fig, zoom, x, y, color=_LOGO_COLOR) -> bool:
    """Add the vector logo to *fig* as a ``PathPatch``.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
    zoom : float
        Logo height as a fraction of the figure (0.03 = 3%).
        Width is derived automatically from the EPS aspect ratio.
    x, y : float
        Bottom-left position in figure-fraction coordinates.
    color : str
        Face colour for the path.

    Returns
    -------
    bool
        ``True`` if the logo was drawn, ``False`` if the EPS was missing.
    """
    path = get_cached_path()
    if path is None:
        return False

    # zoom is the logo height as a fraction of the figure (0.03 = 3%).
    logo_h_frac = zoom

    # Correct for non-square figures: figure-fraction space stretches
    # differently in X vs Y, so we scale X by (fig_h / fig_w) to keep
    # circles circular.
    fig_aspect = fig.get_figheight() / fig.get_figwidth()
    logo_w_frac = logo_h_frac * (_EPS_WIDTH / _EPS_HEIGHT) * fig_aspect

    # Build transform: shift origin to left edge, scale to figure fraction,
    # translate to target (x, y), then into figure coordinates.
    scale_x = logo_w_frac / _EPS_WIDTH
    scale_y = logo_h_frac / _EPS_HEIGHT

    transform = (
        Affine2D().translate(-_EPS_LEFT, 0).scale(scale_x, scale_y).translate(x, y)
        + fig.transFigure
    )

    patch = PathPatch(
        path,
        facecolor=color,
        edgecolor="none",
        clip_on=False,
        transform=transform,
    )
    fig.add_artist(patch)
    return True
