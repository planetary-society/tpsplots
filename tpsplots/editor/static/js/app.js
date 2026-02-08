/**
 * Chart editor entry point.
 * Loads React 19 + RJSF from CDN via import map, renders the editor UI.
 */
import React, { useState, useEffect, useCallback, useRef, createElement } from "react";
import { createRoot } from "react-dom/client";
import htm from "htm";

import {
  fetchSchema,
  fetchDataSchema,
  fetchChartTypes,
  fetchColors,
  fetchDataProfile,
  fetchPreflight,
} from "./api.js";
import { EditorLayout } from "./components/EditorLayout.js";
import { useHotkeys } from "./hooks/useHotkeys.js";

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
];

const PREFLIGHT_DEBOUNCE_MS = 400;

const DEFAULT_STEP_STATUS = {
  data_source_and_preparation: "not_started",
  data_bindings: "not_started",
  visual_design: "not_started",
  annotation_output: "not_started",
};

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
  const [editorHints, setEditorHints] = useState(null);
  const [dataSchema, setDataSchema] = useState(null);
  const [dataUiSchema, setDataUiSchema] = useState(null);
  const [formData, setFormData] = useState({ type: "bar", output: "my_chart", title: "Chart Title" });
  const [dataConfig, setDataConfig] = useState({ source: "" });
  const [currentFile, setCurrentFile] = useState(null);
  const [colors, setColors] = useState({ colors: {}, tps_colors: {} });
  const [toast, setToast] = useState(null);
  const [activeStep, setActiveStep] = useState(1);
  const [stepStatus, setStepStatus] = useState(DEFAULT_STEP_STATUS);
  const [preflight, setPreflight] = useState(null);
  const [dataProfile, setDataProfile] = useState(null);
  const [dataProfileStatus, setDataProfileStatus] = useState("idle");
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [previewDevice, setPreviewDevice] = useState("desktop");
  const [renderTick, setRenderTick] = useState(0);
  const preflightTimerRef = useRef(null);

  // ── Init: load chart types + colors ────────────────────────
  useEffect(() => {
    fetchChartTypes()
      .then(data => setChartTypes(data.types || []))
      .catch(err => console.error("Failed to load chart types:", err));

    fetchColors()
      .then(data => setColors(data))
      .catch(err => console.error("Failed to load colors:", err));

    fetchDataSchema()
      .then((data) => {
        setDataSchema(data.json_schema);
        setDataUiSchema(data.ui_schema);
      })
      .catch(err => console.error("Failed to load data schema:", err));
  }, []);

  // ── Load schema when chart type changes ────────────────────
  useEffect(() => {
    if (!chartType) return;
    fetchSchema(chartType)
      .then(data => {
        setSchema(data.json_schema);
        setUiSchema(data.ui_schema);
        setEditorHints(data.editor_hints || null);
        setFormData(prev => remapAndPruneFormData(prev, chartType, data.json_schema));
      })
      .catch(err => console.error("Failed to load schema:", err));
  }, [chartType]);

  // ── Chart type change handler ──────────────────────────────
  const handleChartTypeChange = useCallback((newType) => {
    setChartType(newType);
    setFormData(prev => ({ ...prev, type: newType }));
    setUnsavedChanges(true);
  }, []);

  const handleFormDataChange = useCallback((next, options = {}) => {
    setFormData(next);
    if (options.markDirty !== false) {
      setUnsavedChanges(true);
    }
  }, []);

  const handleDataConfigChange = useCallback((next, options = {}) => {
    setDataConfig(next);
    if (options.markDirty !== false) {
      setUnsavedChanges(true);
    }
  }, []);

  const handleSaved = useCallback(() => {
    setUnsavedChanges(false);
  }, []);

  const buildConfigNow = useCallback(() => ({ data: dataConfig, chart: formData }), [dataConfig, formData]);

  const runPreflight = useCallback(async () => {
    try {
      const data = await fetchPreflight(buildConfigNow());
      setPreflight(data);
      setStepStatus(data.step_status || DEFAULT_STEP_STATUS);
    } catch (err) {
      const fallback = {
        ready_for_preview: false,
        missing_paths: [],
        blocking_errors: [{ path: "/config", message: err.message || "Preflight failed" }],
        warnings: [],
        step_status: DEFAULT_STEP_STATUS,
      };
      setPreflight(fallback);
      setStepStatus(DEFAULT_STEP_STATUS);
    }
  }, [buildConfigNow]);

  useEffect(() => {
    clearTimeout(preflightTimerRef.current);
    preflightTimerRef.current = setTimeout(() => {
      runPreflight();
    }, PREFLIGHT_DEBOUNCE_MS);
    return () => clearTimeout(preflightTimerRef.current);
  }, [formData, dataConfig, runPreflight]);

  const handleRunDataProfile = useCallback(async () => {
    if (!dataConfig?.source) return;
    setDataProfileStatus("loading");
    try {
      const profile = await fetchDataProfile(dataConfig);
      setDataProfile(profile);
      setDataProfileStatus("success");
    } catch (err) {
      setDataProfile({
        source_kind: "unknown",
        row_count: 0,
        columns: [],
        sample_rows: [],
        warnings: [err.message || "Data profile failed"],
      });
      setDataProfileStatus("error");
    }
  }, [dataConfig]);

  const triggerSave = useCallback(() => {
    window.dispatchEvent(new Event("editor:save"));
  }, []);

  const triggerOpen = useCallback(() => {
    window.dispatchEvent(new Event("editor:open"));
  }, []);

  useHotkeys({
    onSave: triggerSave,
    onOpen: triggerOpen,
    onForceRender: () => setRenderTick((v) => v + 1),
    onSetStep: (step) => setActiveStep(step),
    onToggleDevice: () => setPreviewDevice((d) => (d === "desktop" ? "mobile" : "desktop")),
  });

  // ── Build full config for preview/save ─────────────────────
  const buildFullConfig = useCallback(() => {
    return buildConfigNow();
  }, [buildConfigNow]);

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
      editorHints=${editorHints}
      preflight=${preflight}
      stepStatus=${stepStatus}
      activeStep=${activeStep}
      dataSchema=${dataSchema}
      dataUiSchema=${dataUiSchema}
      dataProfile=${dataProfile}
      dataProfileStatus=${dataProfileStatus}
      previewDevice=${previewDevice}
      renderTick=${renderTick}
      unsavedChanges=${unsavedChanges}
      currentFile=${currentFile}
      colors=${colors}
      toast=${toast}
      onChartTypeChange=${handleChartTypeChange}
      onFormDataChange=${handleFormDataChange}
      onDataConfigChange=${handleDataConfigChange}
      onFileChange=${setCurrentFile}
      onStepChange=${setActiveStep}
      onPreviewDeviceChange=${setPreviewDevice}
      onRunDataProfile=${handleRunDataProfile}
      onSaved=${handleSaved}
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
