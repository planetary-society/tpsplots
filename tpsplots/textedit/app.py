"""FastAPI app for interactive chart text previews."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from tpsplots.textedit.session import TextEditSession

_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>tpsplots textedit</title>
  <style>
    :root {
      --bg: #f2f5f7;
      --panel: #ffffff;
      --border: #d9e0e6;
      --text: #16222e;
      --muted: #536477;
      --accent: #037CC2;
      --error: #A32E2E;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Poppins", "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .layout {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 16px;
      min-height: 100vh;
      padding: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }
    .controls h1 {
      margin: 0 0 6px;
      font-size: 22px;
      line-height: 1.2;
    }
    .controls p {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.4;
    }
    label {
      display: block;
      margin: 12px 0 6px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    input, textarea, select {
      width: 100%;
      padding: 10px 12px;
      font-size: 14px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-family: inherit;
      color: inherit;
      background: #fff;
    }
    textarea {
      min-height: 88px;
      resize: vertical;
    }
    button {
      margin-top: 14px;
      width: 100%;
      padding: 12px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
    }
    button:disabled {
      opacity: 0.55;
      cursor: wait;
    }
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      gap: 12px;
    }
    .preview-header h2 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
    }
    .status {
      color: var(--muted);
      font-size: 12px;
    }
    .status.error {
      color: var(--error);
    }
    #preview {
      border: 1px solid var(--border);
      border-radius: 8px;
      min-height: 540px;
      background: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: auto;
    }
    #preview svg {
      max-width: 100%;
      height: auto;
      display: block;
    }
    @media (max-width: 980px) {
      .layout {
        grid-template-columns: 1fr;
      }
      #preview {
        min-height: 420px;
      }
    }
  </style>
</head>
<body>
  <main class="layout">
    <section class="panel controls">
      <h1>Text Editor</h1>
      <p>Live preview and save for <code>__YAML_PATH__</code></p>

      <label for="device">Device</label>
      <select id="device">
        <option value="desktop">Desktop</option>
        <option value="mobile">Mobile</option>
      </select>

      <label for="title">Title</label>
      <textarea id="title"></textarea>

      <label for="subtitle">Subtitle</label>
      <textarea id="subtitle"></textarea>

      <label for="source">Source</label>
      <input id="source" type="text">

      <button id="saveButton" type="button">Save to YAML</button>
    </section>

    <section class="panel">
      <div class="preview-header">
        <h2>Live Preview</h2>
        <div id="status" class="status">Idle</div>
      </div>
      <div id="preview"></div>
    </section>
  </main>

  <script>
    const initialState = __INITIAL_STATE__;
    const titleEl = document.getElementById("title");
    const subtitleEl = document.getElementById("subtitle");
    const sourceEl = document.getElementById("source");
    const deviceEl = document.getElementById("device");
    const previewEl = document.getElementById("preview");
    const statusEl = document.getElementById("status");
    const saveButton = document.getElementById("saveButton");

    titleEl.value = initialState.title ?? "";
    subtitleEl.value = initialState.subtitle ?? "";
    sourceEl.value = initialState.source ?? "";

    let timer = null;
    let requestCounter = 0;

    async function renderPreview() {
      const requestId = ++requestCounter;
      statusEl.textContent = "Rendering...";
      statusEl.classList.remove("error");

      try {
        const response = await fetch("/api/preview", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            device: deviceEl.value,
            title: titleEl.value,
            subtitle: subtitleEl.value,
            source: sourceEl.value
          })
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Preview failed");
        }
        if (requestId !== requestCounter) {
          return;
        }

        previewEl.innerHTML = payload.svg;
        statusEl.textContent = "Updated";
      } catch (error) {
        if (requestId !== requestCounter) {
          return;
        }
        previewEl.innerHTML = "";
        statusEl.textContent = error.message || "Preview failed";
        statusEl.classList.add("error");
      }
    }

    function queueRender() {
      clearTimeout(timer);
      timer = setTimeout(renderPreview, 250);
    }

    async function saveText() {
      saveButton.disabled = true;
      statusEl.textContent = "Saving...";
      statusEl.classList.remove("error");

      try {
        const response = await fetch("/api/save", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            title: titleEl.value,
            subtitle: subtitleEl.value,
            source: sourceEl.value
          })
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Save failed");
        }
        statusEl.textContent = "Saved";
      } catch (error) {
        statusEl.textContent = error.message || "Save failed";
        statusEl.classList.add("error");
      } finally {
        saveButton.disabled = false;
      }
    }

    for (const element of [titleEl, subtitleEl, sourceEl]) {
      element.addEventListener("input", queueRender);
    }
    deviceEl.addEventListener("change", queueRender);
    saveButton.addEventListener("click", saveText);

    renderPreview();
  </script>
</body>
</html>
"""


class PreviewPayload(BaseModel):
    """Request body for preview rendering."""

    device: Literal["desktop", "mobile"] = "desktop"
    title: str | None = None
    subtitle: str | None = None
    source: str | None = None


class SavePayload(BaseModel):
    """Request body for saving text metadata."""

    title: str
    subtitle: str | None = None
    source: str | None = None


def _render_index_html(session: TextEditSession, yaml_path: Path) -> str:
    """Render HTML UI with initial text values."""
    html_output = _HTML_TEMPLATE.replace("__YAML_PATH__", html.escape(str(yaml_path)))
    html_output = html_output.replace("__INITIAL_STATE__", json.dumps(session.get_initial_text()))
    return html_output


def create_textedit_app(session: TextEditSession, yaml_path: Path) -> FastAPI:
    """Create a FastAPI app bound to a single chart preview session."""
    app = FastAPI(docs_url=None, redoc_url=None, title="tpsplots textedit")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _render_index_html(session, yaml_path)

    @app.post("/api/preview")
    def preview(payload: PreviewPayload) -> dict[str, str]:
        try:
            svg = session.render_svg(
                device=payload.device,
                title=payload.title,
                subtitle=payload.subtitle,
                source=payload.source,
            )
            return {"svg": svg}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/save")
    def save(payload: SavePayload) -> dict[str, str]:
        try:
            session.save_text(
                title=payload.title,
                subtitle=payload.subtitle,
                source=payload.source,
            )
            return {"status": "ok"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app
