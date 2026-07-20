/**
 * Preview panel: device toggle + live PNG preview with debounced rendering.
 *
 * The last successful render stays visible when the config breaks — a banner
 * overlays it and the image desaturates slightly, instead of the chart
 * vanishing mid-edit. The StatusStrip in the header is the single home for
 * preflight state (clickable chips scroll to the offending field).
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { html } from "../lib/html.js";

import { fetchPreview } from "../api.js";
import { StatusStrip } from "./StatusStrip.js";

const DEBOUNCE_MS = 200;
const DEVICES = ["desktop", "mobile", "social"];
const DEVICE_LABELS = { desktop: "Desktop", mobile: "Mobile", social: "Social" };

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
  const [statusDetail, setStatusDetail] = useState(null);
  const [renderedAt, setRenderedAt] = useState(null);

  const timerRef = useRef(null);
  const controllerRef = useRef(null);
  const requestIdRef = useRef(0);

  // Blob URL lifecycle: revoke the previous URL whenever it is replaced, and
  // the final one on unmount. Kept out of setState updaters so revocation is
  // a proper effect (safe under StrictMode double-invocation too).
  const lastUrlRef = useRef(null);
  useEffect(() => {
    const previous = lastUrlRef.current;
    if (previous && previous !== previewUrl) {
      URL.revokeObjectURL(previous);
    }
    lastUrlRef.current = previewUrl;
  }, [previewUrl]);
  useEffect(
    () => () => {
      if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
    },
    []
  );

  const scheduleRender = useCallback(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      const config = buildFullConfig();

      if (!config.data?.source) {
        setStatus("idle");
        setPreviewUrl(null);
        return;
      }

      // Config not currently valid: keep the last-good render on screen and
      // let the StatusStrip explain; skip the doomed request.
      if (preflight && !preflight.ready_for_preview) {
        setStatus("stale");
        return;
      }

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
        setPreviewUrl(blobUrl);
        setStatus("updated");
        setStatusDetail(`${elapsed}s`);
        setRenderedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      } catch (err) {
        if (err.name === "AbortError") return;
        if (currentId !== requestIdRef.current) return;
        // Keep the last-good image; surface the message in the banner.
        setStatus("error");
        setStatusDetail(err.message || "Preview failed");
      }
    }, DEBOUNCE_MS);
  }, [buildFullConfig, device, preflight]);

  useEffect(() => {
    scheduleRender();
    return () => clearTimeout(timerRef.current);
  }, [formData, dataConfig, device, preflight, renderTick, scheduleRender]);

  const hasSource = !!dataConfig?.source;
  const showStale = status === "stale" || status === "error";

  return html`
    <div class="preview-panel">
      <div class="preview-header">
        <h2 class="preview-title">Preview</h2>

        <div class="device-toggle">
          ${DEVICES.map(
            (d) => html`
              <button
                key=${d}
                type="button"
                class="device-btn ${device === d ? "active" : ""}"
                aria-pressed=${device === d}
                title=${d === "social" ? "Social card (no header/footer — rendered for link previews)" : DEVICE_LABELS[d]}
                onClick=${() => onDeviceChange(d)}
              >${DEVICE_LABELS[d]}</button>
            `
          )}
        </div>

        <${StatusStrip} preflight=${preflight} />

        <div class="render-status">
          ${status === "rendering" && html`<span class="spinner-sm"></span>`}
          ${status === "updated" && statusDetail && `Updated ${statusDetail}`}
        </div>
      </div>

      <div class="preview-container">
        ${previewUrl
          ? html`
              <div class="preview-stage ${showStale ? "is-stale" : ""}">
                <img class="preview-img" src=${previewUrl} alt="Chart preview" />
                ${device === "social" &&
                html`<div class="preview-device-note">Social card — no header/footer</div>`}
                ${showStale &&
                html`
                  <div class="preview-banner ${status === "error" ? "is-error" : ""}">
                    ${status === "error"
                      ? statusDetail || "Preview failed"
                      : "Fix the issues above to refresh"}
                    ${renderedAt && html`<span class="preview-banner-time">Showing last successful render · ${renderedAt}</span>`}
                  </div>
                `}
              </div>
            `
          : html`
              <div class="empty-state">
                <img class="empty-state-logo" src="/static/tpsplots-logo.png" alt="tpsplots logo" />
                ${status === "error"
                  ? html`<p class="empty-state-error">${statusDetail || "Preview failed"}</p>`
                  : hasSource
                    ? html`<p>Rendering preview…</p>`
                    : html`<p>Open a YAML file or configure a data source<br/>to see a live preview</p>`}
              </div>
            `}
      </div>
    </div>
  `;
}
