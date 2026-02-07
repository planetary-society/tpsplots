"""Preview API: render chart SVG from config dict."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tpsplots.editor.session import EditorSession

logger = logging.getLogger(__name__)

# Single-threaded executor — matplotlib is not thread-safe.
_executor = ThreadPoolExecutor(max_workers=1)

_PREVIEW_TIMEOUT_SECONDS = 60


class PreviewRequest(BaseModel):
    config: dict[str, Any]
    device: str = "desktop"


def create_preview_router(session: EditorSession) -> APIRouter:
    router = APIRouter(tags=["preview"])

    @router.post("/preview")
    async def preview(payload: PreviewRequest) -> dict:
        """Render a chart preview as SVG."""
        loop = asyncio.get_running_loop()
        try:
            svg = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    session.render_preview,
                    payload.config,
                    payload.device,
                ),
                timeout=_PREVIEW_TIMEOUT_SECONDS,
            )
            return {"svg": svg}
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Preview timed out after {_PREVIEW_TIMEOUT_SECONDS}s",
            ) from exc
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Preview rendering failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/validate")
    def validate(config: dict[str, Any]) -> dict:
        """Validate a config dict and return structured errors."""
        errors = session.validate_config(config)
        return {"valid": len(errors) == 0, "errors": errors}

    return router
