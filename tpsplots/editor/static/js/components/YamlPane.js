/**
 * YAML pane: full-width bottom drawer showing exactly what saving the current
 * config would write (server-rendered via the preflight response, so the
 * comment-preserving merge and protected keys are included).
 *
 * Read-only v1 — the escape hatch for everything the form doesn't cover.
 * Excluded keys (annotations, figsize, matplotlib_config) appear here and are
 * edited in the file itself; "Reload from disk" pulls external edits in.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { html } from "../lib/html.js";
import { useDragResize } from "../hooks/useDragResize.js";

const MIN_HEIGHT = 120;
const MAX_HEIGHT_RATIO = 0.7;
const HEIGHT_KEY = "tpsplots.yamlPane.height";

const maxPaneHeight = () => window.innerHeight * MAX_HEIGHT_RATIO;

export function YamlPane({
  yamlText,
  currentFile,
  lastEditedField,
  onClose,
  onReloadFromDisk,
  showToast,
}) {
  const [height, setHeight] = useState(() => {
    const saved = Number(localStorage.getItem(HEIGHT_KEY));
    return Number.isFinite(saved) && saved >= MIN_HEIGHT ? saved : 280;
  });
  const paneRef = useRef(null);
  const scrollRef = useRef(null);
  const previousFocusRef = useRef(null);

  // Focus management: move focus into the drawer on open, restore on close.
  useEffect(() => {
    previousFocusRef.current = document.activeElement;
    paneRef.current?.focus();
    return () => {
      previousFocusRef.current?.focus?.();
    };
  }, []);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    },
    [onClose]
  );

  // Teach the GUI <-> YAML mapping: when the pane is open and a field was just
  // edited, scroll its YAML key into view.
  useEffect(() => {
    if (!lastEditedField || !scrollRef.current || !yamlText) return;
    const lines = yamlText.split("\n");
    const escaped = lastEditedField.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`^\\s{2}${escaped}:`);
    const lineIdx = lines.findIndex((line) => re.test(line));
    if (lineIdx < 0) return;
    const lineHeight = 18;
    scrollRef.current.scrollTo({ top: Math.max(0, lineIdx * lineHeight - 40), behavior: "smooth" });
  }, [lastEditedField, yamlText]);

  const persistHeight = useCallback(() => {
    setHeight((h) => {
      localStorage.setItem(HEIGHT_KEY, String(Math.round(h)));
      return h;
    });
  }, []);

  const handleResizeStart = useDragResize({
    axis: "y",
    min: MIN_HEIGHT,
    max: maxPaneHeight,
    value: height,
    onChange: setHeight,
    onEnd: persistHeight,
  });

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(yamlText || "");
      showToast("YAML copied");
    } catch {
      showToast("Copy failed", "error");
    }
  }, [yamlText, showToast]);

  return html`
    <div
      ref=${paneRef}
      class="yaml-pane"
      style=${{ height: `${height}px` }}
      tabindex="-1"
      role="region"
      aria-label="YAML view"
      onKeyDown=${handleKeyDown}
    >
      <div class="yaml-pane-resize" onMouseDown=${handleResizeStart} />
      <div class="yaml-pane-header">
        <span class="yaml-pane-title">
          YAML
          ${currentFile && html`<span class="yaml-pane-file">${currentFile}</span>`}
        </span>
        <span class="yaml-pane-hint">
          Shows what Save will write. Fields the form doesn't cover are edited in the file.
        </span>
        <div class="yaml-pane-actions">
          <button type="button" class="btn btn-secondary" onClick=${handleCopy}>
            Copy
          </button>
          ${currentFile &&
          html`
            <button
              type="button"
              class="btn btn-secondary"
              title="Load the file's current contents, replacing unsaved editor changes"
              onClick=${onReloadFromDisk}
            >
              Reload from disk
            </button>
          `}
          <button type="button" class="btn btn-secondary" onClick=${onClose} title="Close (Esc)">
            Close
          </button>
        </div>
      </div>
      <div ref=${scrollRef} class="yaml-pane-scroll">
        ${yamlText
          ? html`<pre class="yaml-pane-code">${yamlText}</pre>`
          : html`<p class="yaml-pane-empty">Configure a chart to see its YAML.</p>`}
      </div>
    </div>
  `;
}
