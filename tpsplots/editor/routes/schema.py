"""Schema API: per-chart-type JSON Schema + uiSchema."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tpsplots.editor.ui_schema import (
    get_available_chart_types,
    get_chart_type_schema,
    get_editor_hints,
    get_ui_schema,
)


def create_schema_router() -> APIRouter:
    router = APIRouter(tags=["schema"])

    @router.get("/schema")
    def schema(type: str = "bar") -> dict:
        """Return JSON Schema and uiSchema for a chart type."""
        try:
            return {
                "json_schema": get_chart_type_schema(type),
                "ui_schema": get_ui_schema(type),
                "editor_hints": get_editor_hints(type),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/chart-types")
    def chart_types() -> dict:
        """Return available chart type strings."""
        return {"types": get_available_chart_types()}

    return router
