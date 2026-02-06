"""Interactive text editing command for chart metadata."""

from __future__ import annotations

import socket
import threading
import webbrowser
from pathlib import Path
from typing import Annotated

import typer


def _pick_available_port(host: str, preferred_port: int) -> int:
    """Return an available port on host.

    If preferred_port is 0, the OS selects an ephemeral port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, preferred_port))
        return int(sock.getsockname()[1])


def start_textedit_server(
    yaml_file: Path, host: str, port: int, open_browser: bool, outdir: Path | None = None
) -> None:
    """Launch the local text editor web app."""
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "textedit requires optional dependencies. Install and sync project dependencies first."
        ) from exc

    try:
        from tpsplots.textedit.app import create_textedit_app
    except ImportError as exc:
        raise RuntimeError(
            "textedit requires optional dependencies. Install and sync project dependencies first."
        ) from exc

    from tpsplots.textedit.session import TextEditSession

    session = TextEditSession(yaml_path=yaml_file, outdir=outdir)
    selected_port = _pick_available_port(host, port)
    app = create_textedit_app(session=session, yaml_path=yaml_file)
    url = f"http://{host}:{selected_port}/"

    typer.echo(f"Text editor running at {url}")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url, new=2)).start()

    uvicorn.run(app, host=host, port=selected_port, log_level="info")


def textedit(
    yaml_file: Annotated[
        Path,
        typer.Argument(
            help="YAML chart configuration file to preview/edit text for",
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host interface for local preview server",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            min=0,
            max=65535,
            help="Port for preview server (0 chooses an available port)",
        ),
    ] = 0,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser",
            help="Automatically open the preview URL in your browser",
        ),
    ] = True,
) -> None:
    """Launch interactive preview for title/subtitle/source text edits."""
    try:
        start_textedit_server(
            yaml_file=yaml_file,
            host=host,
            port=port,
            open_browser=open_browser,
        )
    except OSError as exc:
        typer.echo(f"Failed to bind preview server: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
