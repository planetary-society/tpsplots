/**
 * Chart editor entry point.
 * Loads React 19 + htm from CDN via import map, renders the editor UI.
 */
import { useState, useEffect, useCallback, useRef, Fragment } from "react";
import { createRoot } from "react-dom/client";

import {
  fetchSchema,
  fetchDataSchema,
  fetchChartTypes,
  fetchColors,
  fetchDataProfile,
  fetchPreflight,
  loadYaml,
  saveYaml,
  listFiles,
} from "./api.js";
import { EditorLayout } from "./components/EditorLayout.js";
import { FileMenu, HotkeySheet } from "./components/Header.js";
import { useHotkeys } from "./hooks/useHotkeys.js";
import { html } from "./lib/html.js";

const FIELD_REMAPS = [
  ["x", "categories"],
  ["categories", "x"],
  ["y", "values"],
  ["values", "y"],
  ["color", "colors"],
  ["colors", "color"],
];

const PREFLIGHT_DEBOUNCE_MS = 400;

// ── Session undo ─────────────────────────────────────────────
const MAX_UNDO = 50;
// Rapid same-field edits (typing) within this window coalesce into one entry.
const UNDO_COALESCE_MS = 800;

// ── Recent files (localStorage) ──────────────────────────────
const RECENT_FILES_KEY = "tpsplots.recentFiles";
const MAX_RECENT_FILES = 8;

function readRecentFiles() {
  try {
    const raw = window.localStorage.getItem(RECENT_FILES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((p) => typeof p === "string") : [];
  } catch {
    return [];
  }
}

function writeRecentFiles(list) {
  try {
    window.localStorage.setItem(RECENT_FILES_KEY, JSON.stringify(list.slice(0, MAX_RECENT_FILES)));
  } catch {
    // Storage disabled / over quota — recents are a convenience, not critical.
  }
}

// Normalize a user-typed save path: trim, reject absolute, ensure .yaml/.yml.
// Returns the cleaned path, or null when empty/invalid.
function normalizeSavePath(input) {
  if (input == null) return null;
  let p = String(input).trim();
  if (!p) return null;
  if (p.startsWith("/")) return { error: "Path must be relative (no leading /)" };
  if (!p.endsWith(".yaml") && !p.endsWith(".yml")) p += ".yaml";
  return { path: p };
}

function remapAndPruneFormData(formData, nextType, nextSchema, excludedFields) {
  if (!nextSchema?.properties || !formData) {
    return { ...formData, type: nextType };
  }

  const previousType = formData.type;
  const allowed = new Set(Object.keys(nextSchema.properties));
  // The served schema has excluded-but-valid fields (annotations, figsize,
  // matplotlib_config, ...) stripped server-side. Carry their values through
  // so loading + saving never deletes hand-authored YAML the GUI can't edit.
  const excluded = new Set(excludedFields || []);
  const next = {};

  for (const [key, value] of Object.entries(formData)) {
    if (allowed.has(key) || excluded.has(key)) {
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

  // Type-switch normalization:
  // line -> scatter should not preserve explicit line connectors unless re-added.
  if (previousType !== "scatter" && nextType === "scatter") {
    delete next.linestyle;
  }

  // scatter -> line should restore default line connectors when the scatter
  // config explicitly forced no line.
  if (previousType === "scatter" && nextType === "line") {
    const linestyle = next.linestyle;
    if (typeof linestyle === "string" && linestyle.toLowerCase() === "none") {
      delete next.linestyle;
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
  // Set by EditorLayout to its scroll-to-section function; the Alt+1-3 hotkey
  // calls it directly instead of bouncing a number through component state.
  const sectionJumpRef = useRef(null);
  const [preflight, setPreflight] = useState(null);
  const [dataProfile, setDataProfile] = useState(null);
  const [dataProfileStatus, setDataProfileStatus] = useState("idle");
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [previewDevice, setPreviewDevice] = useState("desktop");
  const [renderTick, setRenderTick] = useState(0);
  const [yamlOpen, setYamlOpen] = useState(false);
  const [lastEditedField, setLastEditedField] = useState(null);
  // File actions + overlays (lifted out of Header — App owns the logic now).
  const [saving, setSaving] = useState(false);
  const [fileMenuOpen, setFileMenuOpen] = useState(false);
  const [files, setFiles] = useState([]);
  const [recentFiles, setRecentFiles] = useState(readRecentFiles);
  const [helpOpen, setHelpOpen] = useState(false);

  const preflightTimerRef = useRef(null);
  const toastTimerRef = useRef(null);
  const requestedTypeRef = useRef(null);
  // Set by the type dropdown, cleared when its schema response is consumed:
  // the schema effect cannot otherwise tell a user type switch (prune + remap
  // formData) from a file load (formData already matches its own type).
  const typeSwitchPendingRef = useRef(false);

  // Undo/redo: bounded stacks of {formData, dataConfig} snapshots.
  const undoStackRef = useRef([]);
  const redoStackRef = useRef([]);
  const lastPushRef = useRef({ time: 0, field: null });
  // Latest committed editable state, so a change handler can snapshot the
  // PREVIOUS state (this ref) before it applies the new one.
  const snapshotRef = useRef({ formData, dataConfig });
  snapshotRef.current = { formData, dataConfig };
  // beforeunload reads dirty state without re-subscribing on every keystroke.
  const unsavedRef = useRef(unsavedChanges);
  unsavedRef.current = unsavedChanges;

  // ── Toast helper ───────────────────────────────────────────
  const showToast = useCallback((message, type = "success") => {
    clearTimeout(toastTimerRef.current);
    setToast({ message, type });
    toastTimerRef.current = setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Recent files ───────────────────────────────────────────
  const pushRecent = useCallback((path) => {
    setRecentFiles((prev) => {
      const next = [path, ...prev.filter((p) => p !== path)].slice(0, MAX_RECENT_FILES);
      writeRecentFiles(next);
      return next;
    });
  }, []);

  // ── Undo bookkeeping ───────────────────────────────────────
  const pushUndo = useCallback((field) => {
    const now = Date.now();
    const last = lastPushRef.current;
    // Coalesce rapid typing in the same top-level field into a single entry.
    if (field && last.field === field && now - last.time < UNDO_COALESCE_MS) {
      lastPushRef.current = { time: now, field };
      return;
    }
    lastPushRef.current = { time: now, field };
    const snap = snapshotRef.current;
    undoStackRef.current.push({ formData: snap.formData, dataConfig: snap.dataConfig });
    if (undoStackRef.current.length > MAX_UNDO) undoStackRef.current.shift();
    // A fresh edit invalidates any redo history.
    redoStackRef.current = [];
  }, []);

  const resetUndo = useCallback(() => {
    undoStackRef.current = [];
    redoStackRef.current = [];
    lastPushRef.current = { time: 0, field: null };
  }, []);

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
    requestedTypeRef.current = chartType;
    fetchSchema(chartType)
      .then(data => {
        // Drop stale responses: rapid A -> B -> A switches must not let the
        // last-resolved (rather than last-requested) schema win.
        if (requestedTypeRef.current !== chartType) return;
        // Prune only when a user type switch requested this schema. Pruning a
        // freshly loaded file against the stripped schema is exactly the path
        // that destroyed hand-authored YAML blocks on save.
        const shouldPrune = typeSwitchPendingRef.current;
        typeSwitchPendingRef.current = false;
        setSchema(data.json_schema);
        setUiSchema(data.ui_schema);
        setEditorHints(data.editor_hints || null);
        setFormData(prev =>
          shouldPrune
            ? remapAndPruneFormData(
                prev,
                chartType,
                data.json_schema,
                data.editor_hints?.excluded_fields
              )
            : prev
        );
      })
      .catch(err => console.error("Failed to load schema:", err));
  }, [chartType]);

  // ── Chart type change handler ──────────────────────────────
  const handleChartTypeChange = useCallback((newType) => {
    pushUndo("type");
    typeSwitchPendingRef.current = true;
    setChartType(newType);
    setUnsavedChanges(true);
  }, [pushUndo]);

  const handleFormDataChange = useCallback((next) => {
    // Track the first changed top-level field (drives YAML-pane scroll AND
    // undo coalescing) against the last committed formData.
    const prev = snapshotRef.current.formData;
    let changedKey = null;
    if (prev && next) {
      const keys = new Set([...Object.keys(prev), ...Object.keys(next)]);
      for (const key of keys) {
        if (prev[key] !== next[key]) {
          changedKey = key;
          break;
        }
      }
    }
    pushUndo(changedKey);
    if (changedKey) setLastEditedField(changedKey);
    setFormData(next);
    setUnsavedChanges(true);
  }, [pushUndo]);

  const handleDataConfigChange = useCallback((next) => {
    pushUndo("data");
    setDataConfig(next);
    setUnsavedChanges(true);
  }, [pushUndo]);

  // Atomic file-load: one handler owns formData + chartType + file + dirty
  // state, instead of three ordered calls whose correctness depended on
  // React batching within a single click handler.
  const applyLoadedConfig = useCallback((config, path) => {
    const chart = config.chart || {};
    typeSwitchPendingRef.current = false;
    setFormData(chart);
    if (chart.type) setChartType(chart.type);
    setDataConfig(config.data || { source: "" });
    setCurrentFile(path);
    setUnsavedChanges(false);
    resetUndo();
  }, [resetUndo]);

  const buildConfigNow = useCallback(() => ({ data: dataConfig, chart: formData }), [dataConfig, formData]);

  // ── Session undo/redo ──────────────────────────────────────
  const restoreSnapshot = useCallback((snap) => {
    // Restoring must not prune formData against the schema, so clear the pending
    // flag before any setChartType the type change would otherwise trigger.
    typeSwitchPendingRef.current = false;
    const snapType = snap.formData?.type;
    setDataConfig(snap.dataConfig);
    setFormData(snap.formData);
    if (snapType && snapType !== chartType) setChartType(snapType);
    setUnsavedChanges(true);
  }, [chartType]);

  // Undo and redo are the same move in opposite directions: pop the source
  // stack, push the current state onto the destination stack.
  const stepHistory = useCallback((fromStackRef, toStackRef) => {
    const stack = fromStackRef.current;
    if (stack.length === 0) return;
    const snap = stack.pop();
    toStackRef.current.push(snapshotRef.current);
    if (toStackRef.current.length > MAX_UNDO) toStackRef.current.shift();
    // Prevent the next edit from coalescing onto a now-restored state.
    lastPushRef.current = { time: 0, field: null };
    restoreSnapshot(snap);
  }, [restoreSnapshot]);

  const handleUndo = useCallback(
    () => stepHistory(undoStackRef, redoStackRef),
    [stepHistory]
  );
  const handleRedo = useCallback(
    () => stepHistory(redoStackRef, undoStackRef),
    [stepHistory]
  );

  // ── Save flow (POST, then handle 409 validation/conflict) ──
  const attemptSave = useCallback(async (path) => {
    const config = buildConfigNow();
    const overrides = {};
    // At most two override rounds (validation + conflict). The server checks
    // conflict before validation, so a doubly-blocked save resolves in ≤3 POSTs.
    for (let round = 0; round < 3; round += 1) {
      try {
        await saveYaml(path, config, overrides);
        return true;
      } catch (err) {
        if (err.status === 409 && err.kind === "validation" && !overrides.override_validation) {
          const ok = window.confirm(
            (err.message || "This chart has validation errors.") +
              "\n\nSave anyway? The file will fail `tpsplots generate` until fixed."
          );
          if (!ok) return false;
          overrides.override_validation = true;
          continue;
        }
        if (err.status === 409 && err.kind === "conflict" && !overrides.override_conflict) {
          const ok = window.confirm(
            "File changed on disk since load. Overwrite it? " +
              "(Cancel to keep the disk version — use Reload from disk.)"
          );
          if (!ok) return false;
          // Override ONLY the conflict — validation stays on.
          overrides.override_conflict = true;
          continue;
        }
        throw err;
      }
    }
    return false;
  }, [buildConfigNow]);

  const doSave = useCallback(async (path) => {
    setSaving(true);
    try {
      const ok = await attemptSave(path);
      if (ok) {
        setCurrentFile(path);
        setUnsavedChanges(false);
        pushRecent(path);
        showToast("Saved to " + path);
      }
      return ok;
    } catch (err) {
      showToast(err.message || "Save failed", "error");
      return false;
    } finally {
      setSaving(false);
    }
  }, [attemptSave, pushRecent, showToast]);

  const promptForPath = useCallback((prefill) => {
    const input = window.prompt("Save as (relative path ending in .yaml):", prefill);
    const result = normalizeSavePath(input);
    if (result == null) return null; // cancelled or empty
    if (result.error) {
      showToast(result.error, "error");
      return null;
    }
    return result.path;
  }, [showToast]);

  const defaultSaveName = useCallback(
    () => (formData?.output ? `${formData.output}.yaml` : "my_chart.yaml"),
    [formData]
  );

  const handleSave = useCallback(async () => {
    // A never-saved chart (no currentFile) prompts for a name first; the
    // backend creates new files.
    const path = currentFile || promptForPath(defaultSaveName());
    if (!path) return;
    await doSave(path);
  }, [currentFile, promptForPath, defaultSaveName, doSave]);

  const handleSaveAs = useCallback(async () => {
    const path = promptForPath(currentFile || defaultSaveName());
    if (!path) return;
    await doSave(path);
  }, [currentFile, promptForPath, defaultSaveName, doSave]);

  const handleOpen = useCallback(async () => {
    try {
      const data = await listFiles();
      setFiles(data.files || []);
      setFileMenuOpen(true);
    } catch (err) {
      showToast("Failed to list files: " + (err.message || err), "error");
    }
  }, [showToast]);

  const handleNew = useCallback(() => {
    if (unsavedChanges && !window.confirm("Discard unsaved changes and start a new chart?")) {
      return;
    }
    typeSwitchPendingRef.current = false;
    setFormData({ type: chartType, output: "my_chart", title: "New Chart" });
    setDataConfig({ source: "" });
    setCurrentFile(null);
    setUnsavedChanges(false);
    resetUndo();
    showToast("New chart");
  }, [unsavedChanges, chartType, resetUndo, showToast]);

  const handleFileSelect = useCallback(async (path) => {
    if (unsavedChanges && !window.confirm("Discard unsaved changes and open " + path + "?")) {
      return;
    }
    setFileMenuOpen(false);
    try {
      const data = await loadYaml(path);
      applyLoadedConfig(data.config, path);
      pushRecent(path);
      showToast("Loaded " + path);
    } catch (err) {
      showToast("Failed to load: " + (err.message || err), "error");
    }
  }, [unsavedChanges, applyLoadedConfig, pushRecent, showToast]);

  const handleEscape = useCallback(() => {
    setHelpOpen(false);
    setFileMenuOpen(false);
  }, []);

  const closeFileMenu = useCallback(() => setFileMenuOpen(false), []);
  const closeHelp = useCallback(() => setHelpOpen(false), []);
  const toggleHelp = useCallback(() => setHelpOpen((v) => !v), []);

  // ── Guard against losing unsaved edits on tab close/reload ─
  useEffect(() => {
    const onBeforeUnload = (e) => {
      if (!unsavedRef.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  // ── Preflight ──────────────────────────────────────────────
  const runPreflight = useCallback(async () => {
    try {
      const data = await fetchPreflight(buildConfigNow(), {
        path: currentFile,
        includeYaml: yamlOpen,
      });
      setPreflight(data);
    } catch (err) {
      setPreflight({
        ready_for_preview: false,
        missing_paths: [],
        blocking_errors: [{ path: "/config", message: err.message || "Preflight failed" }],
        warnings: [],
      });
    }
  }, [buildConfigNow, currentFile, yamlOpen]);

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

  // Auto-fetch data profile when the source changes (e.g. file load, URL paste)
  useEffect(() => {
    if (!dataConfig?.source) {
      setDataProfile(null);
      setDataProfileStatus("idle");
      return;
    }
    handleRunDataProfile();
  }, [dataConfig?.source, handleRunDataProfile]);

  const handleYamlClose = useCallback(() => setYamlOpen(false), []);
  const handleYamlToggle = useCallback(() => setYamlOpen((open) => !open), []);

  useHotkeys({
    onSave: handleSave,
    onOpen: handleOpen,
    onForceRender: () => setRenderTick((v) => v + 1),
    onSetStep: (step) => sectionJumpRef.current?.(step),
    onToggleDevice: () => setPreviewDevice((d) => (d === "desktop" ? "mobile" : "desktop")),
    onToggleYaml: handleYamlToggle,
    onUndo: handleUndo,
    onRedo: handleRedo,
    onToggleHelp: toggleHelp,
    onEscape: handleEscape,
  });

  const handleReloadFromDisk = useCallback(async () => {
    if (!currentFile) return;
    try {
      const data = await loadYaml(currentFile);
      applyLoadedConfig(data.config, currentFile);
      showToast("Reloaded " + currentFile);
    } catch (err) {
      showToast("Reload failed: " + (err.message || err), "error");
    }
  }, [currentFile, applyLoadedConfig, showToast]);

  // ── Render ─────────────────────────────────────────────────
  if (!schema) {
    return html`<div id="loading"><div class="spinner"></div><div>Loading schema…</div></div>`;
  }

  return html`
    <${Fragment}>
      <${EditorLayout}
        chartType=${chartType}
        chartTypes=${chartTypes}
        schema=${schema}
        uiSchema=${uiSchema}
        formData=${formData}
        dataConfig=${dataConfig}
        editorHints=${editorHints}
        preflight=${preflight}
        sectionJumpRef=${sectionJumpRef}
        dataSchema=${dataSchema}
        dataUiSchema=${dataUiSchema}
        dataProfile=${dataProfile}
        dataProfileStatus=${dataProfileStatus}
        previewDevice=${previewDevice}
        renderTick=${renderTick}
        unsavedChanges=${unsavedChanges}
        yamlOpen=${yamlOpen}
        lastEditedField=${lastEditedField}
        onYamlClose=${handleYamlClose}
        onYamlToggle=${handleYamlToggle}
        onReloadFromDisk=${handleReloadFromDisk}
        currentFile=${currentFile}
        colors=${colors}
        toast=${toast}
        saving=${saving}
        onChartTypeChange=${handleChartTypeChange}
        onFormDataChange=${handleFormDataChange}
        onDataConfigChange=${handleDataConfigChange}
        onPreviewDeviceChange=${setPreviewDevice}
        onRunDataProfile=${handleRunDataProfile}
        onSave=${handleSave}
        onSaveAs=${handleSaveAs}
        onOpen=${handleOpen}
        onNew=${handleNew}
        onToggleHelp=${toggleHelp}
        buildFullConfig=${buildConfigNow}
        showToast=${showToast}
      />
      ${fileMenuOpen &&
      html`
        <${FileMenu}
          files=${files}
          recentFiles=${recentFiles}
          onSelect=${handleFileSelect}
          onClose=${closeFileMenu}
        />
      `}
      ${helpOpen && html`<${HotkeySheet} onClose=${closeHelp} />`}
    <//>
  `;
}

// ── Mount ────────────────────────────────────────────────────
window.__editorReady = true;
document.getElementById("loading").style.display = "none";
document.getElementById("root").style.display = "block";

const root = createRoot(document.getElementById("root"));
root.render(html`<${App} />`);
