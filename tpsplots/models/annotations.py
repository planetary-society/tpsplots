"""Chart annotation model — data-space callouts drawn on the primary axes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChartAnnotation(BaseModel):
    """A single text callout anchored in data coordinates.

    Rendered by ``ChartView._apply_annotations`` onto ``fig.axes[0]``. The text
    sits in the same white rounded box as the direct line labels; a gentle,
    thin curved arrow (drawn with the ``drawarrow`` extension) connects the box
    to the anchor point when ``arrow`` is True. ``x`` may be a string for date
    x-axes (parsed with ``pandas.to_datetime``, falling back to the raw value).

    Positioning
    -----------
    When both ``text_x`` and ``text_y`` are given the box is placed there
    verbatim. Otherwise the box starts at the anchor and is nudged by the
    ``adjustText`` extension so multiple label-less callouts don't overlap each
    other or the anchor points.

    Rich text
    ---------
    ``text`` may contain ``flexitext`` style tags to emphasise a phrase, e.g.
    ``"<weight:semibold>$43B</> peak"`` (bold) or ``"<color:#037CC2>NASA</> total"``
    (coloured). A closing ``</>`` ends a tag. Plain strings render as plain text.
    Use sparingly — the box is meant to stand out only when it must.
    """

    x: float | str = Field(..., description="Anchor x position in data coordinates")
    y: float = Field(..., description="Anchor y position in data coordinates")
    text: str = Field(
        ...,
        description=(
            "Callout text. May contain flexitext style tags to emphasise a phrase, "
            "e.g. '<weight:semibold>$43B</> peak'; plain strings render as plain text."
        ),
    )
    text_x: float | str | None = Field(
        None, description="Optional x position for the text box (defaults to the anchor)"
    )
    text_y: float | None = Field(
        None, description="Optional y position for the text box (defaults to the anchor)"
    )
    arrow: bool = Field(
        False, description="Draw a thin curved connector from the box to the anchor point"
    )
    color: str | None = Field(
        None,
        description=(
            "Box border and arrow colour (hex or TPS colour name). Defaults to a "
            "quiet grey; the text ink stays the standard annotation colour."
        ),
    )

    model_config = {"extra": "forbid"}
