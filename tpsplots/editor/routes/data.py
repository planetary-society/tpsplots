"""Data API: data schema, source profiling, and preflight checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tpsplots.editor.session import EditorSession
from tpsplots.editor.ui_schema import get_data_source_schema, get_data_ui_schema
from tpsplots.exceptions import DataSourceError


class DataProfileRequest(BaseModel):
    data: dict[str, Any]


class PreflightRequest(BaseModel):
    config: dict[str, Any]


def create_data_router(session: EditorSession) -> APIRouter:
    router = APIRouter(tags=["data"])

    @router.get("/data-schema")
    def data_schema() -> dict:
        """Return JSON Schema and uiSchema for DataSourceConfig."""
        return {
            "json_schema": get_data_source_schema(),
            "ui_schema": get_data_ui_schema(),
        }

    @router.post("/data-profile")
    def data_profile(payload: DataProfileRequest) -> dict:
        """Resolve a data source and return profile metadata."""
        try:
            return session.profile_data(payload.data)
        except DataSourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/preflight")
    def preflight(payload: PreflightRequest) -> dict:
        """Run guided preflight checks for current editor config."""
        try:
            return session.preflight(payload.config)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
