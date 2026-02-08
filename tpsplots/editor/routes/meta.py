"""Metadata API: colors, templates, and chart type info."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tpsplots.colors import COLORS, TPS_COLORS
from tpsplots.templates import get_available_templates, get_template

# Semantic metadata for TPS brand colours.
# Groups: brand (core identity), neutral (text/bg), accent (lighter variants).
COLOR_SEMANTICS: dict[str, dict[str, str]] = {
    "Neptune Blue": {"group": "brand", "usage": "Primary, baseline, positive"},
    "Rocket Flame": {"group": "brand", "usage": "Threat, cuts, urgency"},
    "Plasma Purple": {"group": "brand", "usage": "Secondary, historical"},
    "Crater Shadow": {"group": "neutral", "usage": "Dark text, emphasis"},
    "Lunar Soil": {"group": "neutral", "usage": "Muted, reference lines"},
    "Comet Dust": {"group": "neutral", "usage": "Light background, grid"},
    "Medium Neptune": {"group": "accent", "usage": "Lighter blue accent"},
    "Light Neptune": {"group": "accent", "usage": "Very light blue, bg"},
    "Medium Plasma": {"group": "accent", "usage": "Lighter purple accent"},
    "Light Plasma": {"group": "accent", "usage": "Very light purple, bg"},
    "Slushy Brine": {"group": "neutral", "usage": "Near-white background"},
    "Black Hole": {"group": "neutral", "usage": "Pure black"},
    "Polar White": {"group": "neutral", "usage": "Pure white"},
}


def create_meta_router() -> APIRouter:
    router = APIRouter(tags=["meta"])

    @router.get("/colors")
    def colors() -> dict:
        """Return TPS brand and semantic color palettes."""
        return {
            "colors": COLORS,
            "tps_colors": TPS_COLORS,
            "color_semantics": COLOR_SEMANTICS,
        }

    @router.get("/templates/{chart_type}")
    def template(chart_type: str) -> dict:
        """Return starter YAML template for a chart type."""
        try:
            yaml_text = get_template(chart_type)
            return {"template": yaml_text}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/templates")
    def available_templates() -> dict:
        """Return list of available template names."""
        return {"templates": get_available_templates()}

    return router
