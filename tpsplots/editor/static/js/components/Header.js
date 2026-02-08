/**
 * Editor header: chart type selector, file name, save button.
 */
import { useState, useCallback, useEffect } from "react";
import { html } from "../lib/html.js";

import { saveYaml, loadYaml, listFiles } from "../api.js";

export function Header(props) {
  const {
    chartType, chartTypes, currentFile,
    onChartTypeChange, onFormDataChange, onDataConfigChange,
    onFileChange, buildFullConfig, showToast, dataConfig,
    onSaved, unsavedChanges = false, preflight,
  } = props;

  const [saving, setSaving] = useState(false);
  const [showFileMenu, setShowFileMenu] = useState(false);
  const [files, setFiles] = useState([]);

  const handleSave = useCallback(async () => {
    if (!currentFile) {
      showToast("No file selected — use Open to load a YAML file first", "error");
      return;
    }
    if (preflight && !preflight.ready_for_preview) {
      const firstMissing = preflight.missing_paths?.[0];
      const firstBlocking = preflight.blocking_errors?.[0];
      const reason = firstMissing
        ? `Missing required field: ${firstMissing}`
        : firstBlocking
          ? firstBlocking.message
          : "Preflight checks failed";
      showToast(`Save blocked: ${reason}`, "error");
      return;
    }
    setSaving(true);
    try {
      const config = buildFullConfig();
      await saveYaml(currentFile, config);
      showToast("Saved to " + currentFile);
      onSaved?.();
    } catch (err) {
      showToast(err.message || "Save failed", "error");
    } finally {
      setSaving(false);
    }
  }, [currentFile, preflight, buildFullConfig, showToast, onSaved]);

  const handleOpen = useCallback(async () => {
    try {
      const data = await listFiles();
      setFiles(data.files || []);
      setShowFileMenu(true);
    } catch (err) {
      showToast("Failed to list files: " + err.message, "error");
    }
  }, [showToast]);

  const handleFileSelect = useCallback(async (path) => {
    setShowFileMenu(false);
    try {
      const data = await loadYaml(path);
      const config = data.config;
      if (config.chart) {
        onFormDataChange(config.chart, { markDirty: false });
        if (config.chart.type) {
          onChartTypeChange(config.chart.type);
        }
      }
      if (config.data) {
        onDataConfigChange(config.data, { markDirty: false });
      }
      onFileChange(path);
      showToast("Loaded " + path);
      onSaved?.();
    } catch (err) {
      showToast("Failed to load: " + err.message, "error");
    }
  }, [onFormDataChange, onDataConfigChange, onChartTypeChange, onFileChange, showToast, onSaved]);

  useEffect(() => {
    const onSaveHotkey = () => handleSave();
    const onOpenHotkey = () => handleOpen();
    window.addEventListener("editor:save", onSaveHotkey);
    window.addEventListener("editor:open", onOpenHotkey);
    return () => {
      window.removeEventListener("editor:save", onSaveHotkey);
      window.removeEventListener("editor:open", onOpenHotkey);
    };
  }, [handleSave, handleOpen]);

  return html`
    <header class="editor-header">
      <div class="header-left">
        <span class="header-logo">tpsplots</span>
      </div>

      <div class="header-center">
        <select
          class="chart-type-select"
          value=${chartType}
          onChange=${(e) => onChartTypeChange(e.target.value)}
        >
          ${chartTypes.map(t => html`<option key=${t} value=${t}>${t}</option>`)}
        </select>
      </div>

      <div class="header-right">
        <button class="btn btn-secondary" onClick=${handleOpen}>Open</button>

        <span class="header-filename">
          ${currentFile || "No file"}
          ${unsavedChanges && html`<span class="header-unsaved-dot" title="Unsaved changes">\u2022</span>`}
        </span>

        <button
          class="btn btn-primary"
          onClick=${handleSave}
          disabled=${saving || !currentFile}
        >
          ${saving ? "Saving…" : "Save"}
        </button>
      </div>

      ${showFileMenu && html`
        <div class="file-menu-overlay" onClick=${() => setShowFileMenu(false)}>
          <div class="file-menu" onClick=${(e) => e.stopPropagation()}>
            <div class="file-menu-header">Open YAML File</div>
            ${files.length === 0
              ? html`<div class="file-menu-empty">No YAML files found</div>`
              : files.map(f => html`
                  <button
                    key=${f}
                    class="file-menu-item"
                    onClick=${() => handleFileSelect(f)}
                  >${f}</button>
                `)
            }
          </div>
        </div>
      `}
    </header>
  `;
}
