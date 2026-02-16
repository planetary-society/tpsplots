"""Interactive chart editor command."""

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


def start_editor_server(
    yaml_dir: Path, host: str, port: int, open_browser: bool, outdir: Path | None = None
) -> None:
    """Launch the chart editor web app."""
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "editor requires optional dependencies. Install with: uv sync --extra dev"
        ) from exc

    from tpsplots.editor.app import create_editor_app
    from tpsplots.editor.session import EditorSession

    session = EditorSession(yaml_dir=yaml_dir, outdir=outdir)
    selected_port = _pick_available_port(host, port)
    app = create_editor_app(session)
    url = f"http://{host}:{selected_port}/"

    typer.echo(f"Chart editor running at {url}")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url, new=2)).start()

    uvicorn.run(app, host=host, port=selected_port, log_level="info")


def editor(
    yaml_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory containing YAML chart configurations",
            exists=True,
            file_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = Path("yaml"),
    host: Annotated[
        str,
        typer.Option("--host", help="Host interface for the editor server"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            min=0,
            max=65535,
            help="Port for the editor server (0 chooses an available port)",
        ),
    ] = 0,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser",
            help="Automatically open the editor URL in your browser",
        ),
    ] = True,
) -> None:
    """Launch the interactive chart editor."""
    try:
        start_editor_server(
            yaml_dir=yaml_dir,
            host=host,
            port=port,
            open_browser=open_browser,
        )
    except OSError as exc:
        typer.echo(f"Failed to bind editor server: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
