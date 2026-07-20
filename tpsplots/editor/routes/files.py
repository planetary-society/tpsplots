"""File API: load, save, and list YAML files."""

from __future__ import annotations

from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from tpsplots.editor.session import EditorSession, SaveConflict, SaveValidationError


class SaveRequest(BaseModel):
    path: str
    config: dict[str, Any]
    # Separable override intents matching the two 409 kinds: a client that
    # receives kind=conflict can override just the conflict without also
    # disabling validation (and vice versa).
    override_conflict: bool = False
    override_validation: bool = False


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
        except yaml.YAMLError as exc:
            raise HTTPException(status_code=400, detail=f"Malformed YAML: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/save")
    def save(payload: SaveRequest):
        """Save config to a YAML file.

        Returns 409 when the save is blocked by config validation (``kind:
        validation``, with structured ``errors``) or by an on-disk change since
        the file was loaded (``kind: conflict``). Path/suffix errors are 400.
        """
        try:
            session.save_yaml(
                payload.path,
                payload.config,
                override_conflict=payload.override_conflict,
                override_validation=payload.override_validation,
            )
            return {"status": "ok"}
        except SaveConflict:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "File changed on disk since it was loaded — reload or overwrite.",
                    "kind": "conflict",
                },
            )
        except SaveValidationError as exc:
            return JSONResponse(
                status_code=409,
                content={"detail": str(exc), "kind": "validation", "errors": exc.errors},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/files")
    def list_files() -> dict:
        """List YAML files in the yaml directory.

        Each ``files`` entry is enriched: ``{"path", "type", "title"}`` where
        ``type``/``title`` come from the file's ``chart`` block (``None`` when the
        file is unreadable or has no chart section).
        """
        return {"files": session.list_yaml_files()}

    return router
