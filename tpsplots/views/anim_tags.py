"""Inert animation tags for data artists.

The animation layer (``tpsplots/animation/``) needs to find the *data* artists a
view drew — the line for each series, the rectangle for each bar, the endpoint
marker, the value label — so it can mutate their geometry/alpha frame by frame.
The raw matplotlib containers (``ax.lines`` / ``ax.patches`` / ``ax.texts`` /
``ax.collections``) mix those data artists with reference lines, gridline proxies,
legend handles and other chrome, and telling them apart with position/type
heuristics is fragile. Instead, each view *tags* the artists it cares about at
draw time with a small frozen :class:`Tag` describing the artist's role and its
index within the series/category ordering.

Why a plain Python attribute (``artist._tps_anim``) rather than
``artist.set_gid(...)``? ``set_gid`` leaks the id into rendered SVG output as a
``<g id=...>`` wrapper, changing the bytes of every static export. A bare
attribute is completely inert: matplotlib's Agg/SVG/PDF backends never read it,
so tagged figures produce byte-identical SVG/PNG/PPTX. Tagging is therefore a
no-op for all static output — it only matters to code that explicitly calls
:func:`get_tag` / :func:`iter_tagged`.

Why does this module live in ``views/`` and not under ``animation/``? The import
direction must stay strictly *animation → views*: ``views/__init__`` eagerly
imports every view module, and the animation renderer imports the processor which
imports views. If views imported anything from ``animation/`` we'd create a latent
circular-import trap. Keeping the tag helpers here (stdlib-only, no matplotlib
import, artists duck-typed) lets views tag without ever importing ``animation/``.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

#: Attribute name under which the :class:`Tag` is stashed on an artist.
ANIM_ATTR = "_tps_anim"


class Roles:
    """String role constants identifying what a tagged artist represents."""

    SERIES = "series"
    ENDPOINT = "endpoint"
    # Decorative orbit ring around an endpoint. Kept distinct from ENDPOINT —
    # the line animator's endpoint lookup is one-artist-per-series-index.
    ENDPOINT_RING = "endpoint_ring"
    SERIES_LABEL = "series_label"
    BAR = "bar"
    VALUE_LABEL = "value_label"
    BAR_SEGMENT = "bar_segment"
    SEGMENT_LABEL = "segment_label"
    STACK_LABEL = "stack_label"
    STEM = "stem"
    END_MARKER = "end_marker"


@dataclass(frozen=True)
class Tag:
    """Immutable descriptor attached to a data artist for the animation layer.

    Attributes:
        role: One of the :class:`Roles` constants.
        index: Position of the artist within its series/category ordering.
        meta: Optional extra data (orientation, baseline, layer, etc.).
    """

    role: str
    index: int = 0
    meta: Mapping[str, object] = field(default_factory=dict)


def tag_artist(artist: Any, role: str, index: int = 0, **meta: object) -> None:
    """Stamp ``artist`` with a :class:`Tag` under :data:`ANIM_ATTR`.

    Inert for static rendering: the attribute is never read by any matplotlib
    backend, so it does not affect SVG/PNG/PPTX output.
    """
    # **meta already allocated a fresh dict owned by this call — store it as-is
    # (tagging runs for every data artist in every static render).
    setattr(artist, ANIM_ATTR, Tag(role=role, index=index, meta=meta))


def get_tag(artist: Any) -> Tag | None:
    """Return the :class:`Tag` attached to ``artist``, or ``None`` if untagged."""
    return getattr(artist, ANIM_ATTR, None)


def iter_tagged(fig: Any) -> Iterator[tuple[Tag, Any]]:
    """Yield ``(tag, artist)`` for tagged artists in ``fig``'s axes containers.

    Scans each axes' ``lines``, ``patches``, ``collections`` and ``texts`` only.
    Tagged artists MUST land in one of those containers (every current tag site
    does); artists added elsewhere (``ax.add_artist``, figure-level text) are
    not found.
    """
    for ax in fig.get_axes():
        for container in (ax.lines, ax.patches, ax.collections, ax.texts):
            for artist in container:
                tag = get_tag(artist)
                if tag is not None:
                    yield tag, artist
