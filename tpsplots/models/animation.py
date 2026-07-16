"""Validated configuration for the optional ``animation:`` YAML section."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AnimationConfig(BaseModel):
    """Optional top-level ``animation:`` section for ``tpsplots animate``.

    All fields default to ``None`` ("unset") — concrete defaults live ONLY in
    :data:`tpsplots.animation.config.DEFAULTS` so that CLI > YAML > defaults
    precedence can distinguish an unset value from one explicitly set to the
    same value as the default. Setting real defaults here would make that
    distinction impossible and guarantee drift between two sources of truth.

    This section is ignored by static generation (``generate``/``validate`` and
    the editor); only ``tpsplots animate`` reads it.
    """

    model_config = ConfigDict(extra="forbid")

    formats: list[Literal["landscape", "portrait", "square"]] | None = Field(
        None, description="Video aspect ratios to render (default: square 1080x1080)"
    )
    fps: int | None = Field(None, ge=1, le=120, description="Frames per second of the output video")
    duration: float | None = Field(
        None, gt=0, description="Draw-phase seconds (not total video length)"
    )
    stagger: float | None = Field(
        None, ge=0, description="Seconds between successive series/elements starting to animate"
    )
    easing: (
        Literal[
            "linear",
            "cubic_in_out",
            "quint_in_out",
            "expo_in_out",
            "cubic_out",
            "quart_out",
            "quint_out",
            "back_out",
            "back_out_soft",
            "glide_pop",
        ]
        | None
    ) = Field(None, description="Named easing curve for the draw phase")
    intro_hold: float | None = Field(
        None, ge=0, description="Seconds before data animation begins (grid/axis fade-in)"
    )
    end_hold: float | None = Field(
        None, ge=0, description="Seconds to hold the finished chart at the end of the video"
    )
    quality: Literal["high", "draft"] | None = Field(
        None, description="Encoding quality preset (draft is faster and forces 30fps)"
    )
