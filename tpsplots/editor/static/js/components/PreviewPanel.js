/**
 * Preview panel: device toggle + live SVG preview with debounced rendering.
 */
import { useState, useEffect, useRef, useCallback, createElement } from "react";
import htm from "htm";

import { fetchPreview } from "../api.js";

const html = htm.bind(createElement);

const DEBOUNCE_MS = 800;

export function PreviewPanel({ buildFullConfig, formData, dataConfig }) {
  const [device, setDevice] = useState("desktop");
  const [svg, setSvg] = useState("");
  const [status, setStatus] = useState("idle");
  const [renderTime, setRenderTime] = useState(null);

  const timerRef = useRef(null);
  const controllerRef = useRef(null);
  const requestIdRef = useRef(0);

  // Debounced preview render
  const scheduleRender = useCallback(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const config = buildFullConfig();

      // Skip if no data source configured
      if (!config.data?.source) {
        setStatus("idle");
        setSvg("");
        return;
      }

      // Cancel previous request
      if (controllerRef.current) {
        controllerRef.current.abort();
      }
      controllerRef.current = new AbortController();

      const currentId = ++requestIdRef.current;
      setStatus("rendering");
      const startTime = performance.now();

      try {
        const data = await fetchPreview(config, device, controllerRef.current.signal);
        if (currentId !== requestIdRef.current) return;

        const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
        setSvg(data.svg);
        setStatus("updated");
        setRenderTime(elapsed);
      } catch (err) {
        if (err.name === "AbortError") return;
        if (currentId !== requestIdRef.current) return;
        setStatus("error");
        setSvg("");
        setRenderTime(err.message || "Preview failed");
      }
    }, DEBOUNCE_MS);
  }, [buildFullConfig, device]);

  // Re-render when formData, dataConfig, or device changes
  useEffect(() => {
    scheduleRender();
    return () => clearTimeout(timerRef.current);
  }, [formData, dataConfig, device, scheduleRender]);

  const statusText = {
    idle: "Configure a data source to see preview",
    rendering: "Rendering…",
    updated: `Updated ${renderTime}s`,
    error: renderTime || "Preview failed",
  }[status] || "";

  const hasSource = !!dataConfig?.source;

  return html`
    <div class="preview-panel">
      <div class="preview-header">
        <h2 class="preview-title">Preview</h2>

        <div class="device-toggle">
          <button
            class="device-btn ${device === "desktop" ? "active" : ""}"
            onClick=${() => setDevice("desktop")}
          >Desktop</button>
          <button
            class="device-btn ${device === "mobile" ? "active" : ""}"
            onClick=${() => setDevice("mobile")}
          >Mobile</button>
        </div>

        <div class="status ${status === "error" ? "error" : ""}">
          ${status === "rendering" && html`<span class="spinner-sm"></span>`}
          ${statusText}
        </div>
      </div>

      <div class="preview-container">
        ${svg
          ? html`<div class="preview-card" dangerouslySetInnerHTML=${{ __html: svg }} />`
          : html`
              <div class="empty-state">
                ${hasSource
                  ? html`<p>Loading preview…</p>`
                  : html`<p>Open a YAML file or configure a data source<br/>to see a live preview</p>`
                }
              </div>
            `
        }
      </div>
    </div>
  `;
}
