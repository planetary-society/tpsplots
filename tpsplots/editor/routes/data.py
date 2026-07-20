"""Data API: data schema, source profiling, and preflight checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tpsplots.editor.session import EditorSession
from tpsplots.editor.ui_schema import get_data_source_schema, get_data_ui_schema
from tpsplots.exceptions import DataSourceError, TPSPlotsError


class DataProfileRequest(BaseModel):
    data: dict[str, Any]


class PreflightRequest(BaseModel):
    config: dict[str, Any]
    # YAML-pane support: when include_yaml is set, the response carries a
    # yaml_preview of exactly what saving to `path` would write. Piggybacked
    # on preflight (which already runs per debounced edit) so the pane does
    # not add another request stream; costs nothing while the pane is closed.
    path: str | None = None
    include_yaml: bool = False


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
            result = session.preflight(payload.config)
            if payload.include_yaml:
                try:
                    result["yaml_preview"] = session.render_save_output(
                        payload.config, payload.path
                    )
                except Exception as exc:
                    # The pane is a convenience view — a preview failure must
                    # not fail preflight itself.
                    result["yaml_preview"] = None
                    result["warnings"] = [*result.get("warnings", []), f"YAML preview: {exc}"]
            return result
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except TPSPlotsError as exc:
            # Config/data errors are user-fixable input problems — return 400
            # with the message rather than a 500.
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/refresh-data")
    def refresh_data() -> dict:
        """Clear cached data/profiles so changed sources are re-read."""
        try:
            session.invalidate_data_cache()
            return {"status": "ok"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
