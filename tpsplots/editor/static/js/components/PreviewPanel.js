/**
 * Preview panel: device toggle + live PNG preview with debounced rendering.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { html } from "../lib/html.js";

import { fetchPreview } from "../api.js";
import { PreflightPanel } from "./PreflightPanel.js";

const DEBOUNCE_MS = 200;

export function PreviewPanel({
  buildFullConfig,
  formData,
  dataConfig,
  device,
  onDeviceChange,
  preflight,
  renderTick = 0,
}) {
  const [previewUrl, setPreviewUrl] = useState(null);
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
        setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
        return;
      }

      // Preflight gating (required fields + blocking issues)
      if (preflight && !preflight.ready_for_preview) {
        setStatus("error");
        setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
        setRenderTime("Resolve preflight issues first");
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
        const blobUrl = await fetchPreview(config, device, controllerRef.current.signal);
        if (currentId !== requestIdRef.current) {
          URL.revokeObjectURL(blobUrl);
          return;
        }

        const elapsed = ((performance.now() - startTime) / 1000).toFixed(1);
        setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return blobUrl; });
        setStatus("updated");
        setRenderTime(elapsed);
      } catch (err) {
        if (err.name === "AbortError") return;
        if (currentId !== requestIdRef.current) return;
        setStatus("error");
        setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
        setRenderTime(err.message || "Preview failed");
      }
    }, DEBOUNCE_MS);
  }, [buildFullConfig, device, preflight]);

  // Re-render when formData, dataConfig, or device changes
  useEffect(() => {
    scheduleRender();
    return () => clearTimeout(timerRef.current);
  }, [formData, dataConfig, device, preflight, renderTick, scheduleRender]);

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
            type="button"
            class="device-btn ${device === "desktop" ? "active" : ""}"
            aria-pressed=${device === "desktop"}
            onClick=${() => onDeviceChange("desktop")}
          >Desktop</button>
          <button
            type="button"
            class="device-btn ${device === "mobile" ? "active" : ""}"
            aria-pressed=${device === "mobile"}
            onClick=${() => onDeviceChange("mobile")}
          >Mobile</button>
        </div>

        <div class="status ${status === "error" ? "error" : ""}">
          ${status === "rendering" && html`<span class="spinner-sm"></span>`}
          ${statusText}
        </div>
      </div>

      <div class="preview-container">
        ${preflight && !preflight.ready_for_preview
          ? html`<${PreflightPanel} preflight=${preflight} />`
          : previewUrl
          ? html`<img class="preview-img" src=${previewUrl} alt="Chart preview" />`
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
