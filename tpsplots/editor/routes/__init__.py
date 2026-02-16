"""Editor API route modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from tpsplots.editor.routes.data import create_data_router
from tpsplots.editor.routes.files import create_files_router
from tpsplots.editor.routes.meta import create_meta_router
from tpsplots.editor.routes.preview import create_preview_router
from tpsplots.editor.routes.schema import create_schema_router

if TYPE_CHECKING:
    from tpsplots.editor.session import EditorSession


def create_api_router(session: EditorSession) -> APIRouter:
    """Aggregate all editor API sub-routers."""
    router = APIRouter(prefix="/api")
    router.include_router(create_schema_router())
    router.include_router(create_data_router(session))
    router.include_router(create_preview_router(session))
    router.include_router(create_files_router(session))
    router.include_router(create_meta_router())
    return router
