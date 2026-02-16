"""File API: load, save, and list YAML files."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tpsplots.editor.session import EditorSession


class SaveRequest(BaseModel):
    path: str
    config: dict[str, Any]


def create_files_router(session: EditorSession) -> APIRouter:
    router = APIRouter(tags=["files"])

    @router.get("/load")
    def load(path: str) -> dict:
        """Load a YAML file as JSON."""
        try:
            config = session.load_yaml(path)
            return {"config": config}
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/save")
    def save(payload: SaveRequest) -> dict:
        """Save config to a YAML file."""
        try:
            session.save_yaml(payload.path, payload.config)
            return {"status": "ok"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/files")
    def list_files() -> dict:
        """List YAML files in the yaml directory."""
        return {"files": session.list_yaml_files()}

    return router
