/**
 * Chart editor entry point.
 * Loads React 19 + RJSF from CDN via import map, renders the editor UI.
 */
import React, { useState, useEffect, useCallback, useRef, createElement } from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";

import { fetchSchema, fetchChartTypes, fetchColors } from "./api.js";
import { EditorLayout } from "./components/EditorLayout.js";

const html = htm.bind(createElement);

// Re-export html for use by all components
export { html, React };

const FIELD_REMAPS = [
  ["x", "categories"],
  ["categories", "x"],
  ["y", "values"],
  ["values", "y"],
  ["color", "colors"],
  ["colors", "color"],
  ["label", "labels"],
  ["labels", "label"],
];

function remapAndPruneFormData(formData, nextType, nextSchema) {
  if (!nextSchema?.properties || !formData) {
    return { ...formData, type: nextType };
  }

  const allowed = new Set(Object.keys(nextSchema.properties));
  const next = {};

  for (const [key, value] of Object.entries(formData)) {
    if (allowed.has(key)) {
      next[key] = value;
    }
  }

  for (const [from, to] of FIELD_REMAPS) {
    if (!allowed.has(to) || next[to] !== undefined) {
      continue;
    }
    const value = formData[from];
    if (value !== undefined && value !== null && value !== "") {
      next[to] = value;
    }
  }

  next.type = nextType;
  return next;
}

function App() {
  // ── State ──────────────────────────────────────────────────
  const [chartType, setChartType] = useState("bar");
  const [chartTypes, setChartTypes] = useState([]);
  const [schema, setSchema] = useState(null);
  const [uiSchema, setUiSchema] = useState(null);
  const [formData, setFormData] = useState({ type: "bar", output: "my_chart", title: "Chart Title" });
  const [dataConfig, setDataConfig] = useState({ source: "" });
  const [currentFile, setCurrentFile] = useState(null);
  const [colors, setColors] = useState({ colors: {}, tps_colors: {} });
  const [toast, setToast] = useState(null);

  // ── Init: load chart types + colors ────────────────────────
  useEffect(() => {
    fetchChartTypes()
      .then(data => setChartTypes(data.types || []))
      .catch(err => console.error("Failed to load chart types:", err));

    fetchColors()
      .then(data => setColors(data))
      .catch(err => console.error("Failed to load colors:", err));
  }, []);

  // ── Load schema when chart type changes ────────────────────
  useEffect(() => {
    if (!chartType) return;
    fetchSchema(chartType)
      .then(data => {
        setSchema(data.json_schema);
        setUiSchema(data.ui_schema);
        setFormData(prev => remapAndPruneFormData(prev, chartType, data.json_schema));
      })
      .catch(err => console.error("Failed to load schema:", err));
  }, [chartType]);

  // ── Chart type change handler ──────────────────────────────
  const handleChartTypeChange = useCallback((newType) => {
    setChartType(newType);
    setFormData(prev => ({ ...prev, type: newType }));
  }, []);

  // ── Build full config for preview/save ─────────────────────
  const buildFullConfig = useCallback(() => {
    return {
      data: dataConfig,
      chart: formData,
    };
  }, [dataConfig, formData]);

  // ── Toast helper ───────────────────────────────────────────
  const showToast = useCallback((message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Render ─────────────────────────────────────────────────
  if (!schema) {
    return html`<div id="loading"><div class="spinner"></div><div>Loading schema…</div></div>`;
  }

  return html`
    <${EditorLayout}
      chartType=${chartType}
      chartTypes=${chartTypes}
      schema=${schema}
      uiSchema=${uiSchema}
      formData=${formData}
      dataConfig=${dataConfig}
      currentFile=${currentFile}
      colors=${colors}
      toast=${toast}
      onChartTypeChange=${handleChartTypeChange}
      onFormDataChange=${setFormData}
      onDataConfigChange=${setDataConfig}
      onFileChange=${setCurrentFile}
      buildFullConfig=${buildFullConfig}
      showToast=${showToast}
    />
  `;
}

// ── Mount ────────────────────────────────────────────────────
window.__editorReady = true;
document.getElementById("loading").style.display = "none";
document.getElementById("root").style.display = "block";

const root = createRoot(document.getElementById("root"));
root.render(html`<${App} />`);
