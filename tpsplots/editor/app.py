"""FastAPI app factory for the chart editor."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from tpsplots.editor.routes import create_api_router
from tpsplots.editor.session import EditorSession

_EDITOR_DIR = Path(__file__).parent
_STATIC_DIR = _EDITOR_DIR / "static"
_TEMPLATE_PATH = _EDITOR_DIR / "templates" / "editor.html"

# Content Security Policy — no CORS middleware because any website in the
# same browser could call localhost APIs and overwrite YAML files.
_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://esm.sh 'unsafe-inline'; "
    "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
    "font-src https://fonts.gstatic.com; "
    "connect-src 'self' https://esm.sh; "
    "img-src 'self' data: blob:; "
    "frame-src 'none'; "
    "object-src 'none'"
)


def create_editor_app(session: EditorSession) -> FastAPI:
    """Create the chart editor FastAPI application."""
    app = FastAPI(
        title="tpsplots editor",
        docs_url=None,
        redoc_url=None,
    )

    # GZip compression for API responses (JSON, PNG)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Mount static assets
    if _STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # API routes
    app.include_router(create_api_router(session))

    # CSP middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    # Serve editor HTML
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _TEMPLATE_PATH.read_text(encoding="utf-8")

    return app
