"""Metadata API: colors, templates, and chart type info."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tpsplots.colors import COLORS, TPS_COLORS
from tpsplots.templates import get_available_templates, get_template


def create_meta_router() -> APIRouter:
    router = APIRouter(tags=["meta"])

    @router.get("/colors")
    def colors() -> dict:
        """Return TPS brand and semantic color palettes."""
        return {"colors": COLORS, "tps_colors": TPS_COLORS}

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
