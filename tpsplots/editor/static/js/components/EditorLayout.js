/**
 * Main editor layout: header + split pane (form | preview) + YAML drawer.
 *
 * The form panel is three always-visible sections — Data / Chart / Text —
 * with a sticky scrollspy chip-nav. No gating: sections never lock; before
 * data is loaded the Chart section explains what loading unlocks instead of
 * disabling inputs. Preflight state lives in ONE place (the StatusStrip in
 * the preview header), with per-section issue badges on the nav chips.
 */
import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { html } from "../lib/html.js";
import { sectionForPath } from "../lib/preflightPaths.js";
import { useDragResize } from "../hooks/useDragResize.js";

import { Header } from "./Header.js";
import { YamlPane } from "./YamlPane.js";
import { TieredVisualDesign } from "./TieredVisualDesign.js";
import { MetadataSection } from "./MetadataSection.js";
import { PreviewPanel } from "./PreviewPanel.js";
import { DataSourceStep } from "./DataSourceStep.js";
import { BindingStep } from "./BindingStep.js";
import { Toast } from "./Toast.js";

const SECTIONS = [
  { id: "data", label: "Data" },
  { id: "chart", label: "Chart" },
  { id: "text", label: "Text & Output" },
];

export function EditorLayout(props) {
  const {
    chartType, chartTypes, schema, uiSchema, formData, dataConfig,
    currentFile, colors, toast,
    editorHints, preflight, sectionJumpRef,
    dataSchema, dataUiSchema, dataProfile, dataProfileStatus,
    previewDevice, renderTick, unsavedChanges,
    yamlOpen, lastEditedField, onYamlClose, onYamlToggle, onReloadFromDisk,
    onChartTypeChange, onFormDataChange, onDataConfigChange,
    onPreviewDeviceChange,
    onRunDataProfile, buildFullConfig, showToast,
    saving, onSave, onSaveAs, onOpen, onNew, onToggleHelp,
  } = props;

  // Resize state
  const [formWidth, setFormWidth] = useState(460);
  const [isResizing, setIsResizing] = useState(false);
  const [activeSection, setActiveSection] = useState("data");
  const formPanelRef = useRef(null);
  const sectionRefs = useRef({});

  const startResizing = useCallback(() => setIsResizing(true), []);
  const stopResizing = useCallback(() => setIsResizing(false), []);
  const handleResizeStart = useDragResize({
    axis: "x",
    min: 320,
    max: 680,
    value: formWidth,
    onChange: setFormWidth,
    onStart: startResizing,
    onEnd: stopResizing,
  });

  const visualDesignFields = useMemo(
    () => new Set(editorHints?.step_field_map?.visual_design || []),
    [editorHints]
  );

  const textFields = useMemo(
    () => new Set(editorHints?.step_field_map?.annotation_output || []),
    [editorHints]
  );

  // Per-section issue badges, derived client-side from the paths the strip
  // already renders (no second server-side taxonomy).
  const sectionIssues = useMemo(() => {
    const counts = { data: 0, chart: 0, text: 0 };
    if (!preflight) return counts;
    const paths = [
      ...(preflight.blocking_errors || []).map((e) => e.path),
      ...(preflight.missing_paths || []),
    ];
    for (const path of paths) {
      counts[sectionForPath(path, textFields)] += 1;
    }
    return counts;
  }, [preflight, textFields]);

  // The SeriesTable owns per-series styling on line/scatter — its correlated
  // fields are excluded from the tiered form unconditionally so a value is
  // never editable in two places (even with a single series).
  const seriesCorrelated = editorHints?.series_correlated_fields;
  const seriesExcludedFields = seriesCorrelated?.correlated || null;

  const fieldTiers = editorHints?.field_tiers;
  const compositeWidgets = editorHints?.composite_widgets;

  const dataReady = !!dataProfile && (dataProfile.columns || []).length > 0;

  // Scrollspy: track which section heading is nearest the top of the panel.
  useEffect(() => {
    const rootEl = formPanelRef.current;
    if (!rootEl) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveSection(visible[0].target.dataset.section);
      },
      { root: rootEl, rootMargin: "-10% 0px -70% 0px" }
    );
    for (const section of SECTIONS) {
      const el = sectionRefs.current[section.id];
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, []);

  const scrollToSection = useCallback((id) => {
    const el = sectionRefs.current[id];
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    // Move focus for keyboard/AT users; heading carries tabindex="-1".
    el.querySelector("h3")?.focus?.();
    setActiveSection(id);
  }, []);

  // Alt+1..3: expose the jump function to App's hotkey layer via ref — a
  // direct call, not a number bounced through component state.
  useEffect(() => {
    if (!sectionJumpRef) return undefined;
    sectionJumpRef.current = (n) => {
      const section = SECTIONS[n - 1];
      if (section) scrollToSection(section.id);
    };
    return () => {
      sectionJumpRef.current = null;
    };
  }, [sectionJumpRef, scrollToSection]);

  const registerSection = useCallback(
    (id) => (el) => {
      sectionRefs.current[id] = el;
    },
    []
  );

  return html`
    <${Header}
      chartType=${chartType}
      chartTypes=${chartTypes}
      currentFile=${currentFile}
      onChartTypeChange=${onChartTypeChange}
      onSave=${onSave}
      onSaveAs=${onSaveAs}
      onOpen=${onOpen}
      onNew=${onNew}
      onToggleHelp=${onToggleHelp}
      saving=${saving}
      unsavedChanges=${unsavedChanges}
      yamlOpen=${yamlOpen}
      onToggleYaml=${onYamlToggle}
    />

    <div class="editor-layout" style=${{ gridTemplateColumns: `${formWidth}px 6px 1fr` }}>
      <div class="form-panel" ref=${formPanelRef}>
        <nav class="section-nav" aria-label="Chart sections">
          ${SECTIONS.map((section) => {
            const issues = sectionIssues[section.id];
            return html`
              <button
                key=${section.id}
                type="button"
                class="section-chip ${activeSection === section.id ? "active" : ""}"
                onClick=${() => scrollToSection(section.id)}
              >
                ${section.label}
                ${issues > 0 && html`<span class="section-chip-badge">${issues}</span>`}
              </button>
            `;
          })}
        </nav>

        <section
          class="editor-section"
          data-section="data"
          ref=${registerSection("data")}
        >
          <div class="editor-section-header">
            <h3 tabindex="-1">Data</h3>
            <p>Load a source, then shape its columns.</p>
          </div>
          <${DataSourceStep}
            dataSchema=${dataSchema}
            dataUiSchema=${dataUiSchema}
            dataConfig=${dataConfig}
            onDataConfigChange=${onDataConfigChange}
            onTestSource=${onRunDataProfile}
            profile=${dataProfile}
            profileStatus=${dataProfileStatus}
          />
        </section>

        <section
          class="editor-section"
          data-section="chart"
          ref=${registerSection("chart")}
        >
          <div class="editor-section-header">
            <h3 tabindex="-1">Chart</h3>
            <p>Bind columns, then style the result.</p>
          </div>
          ${!dataReady &&
          html`
            <div class="section-note">
              <span>Load data to get column suggestions and checks.</span>
              <button
                type="button"
                class="btn btn-secondary"
                onClick=${() => scrollToSection("data")}
              >Go to Data</button>
            </div>
          `}
          <${BindingStep}
            schema=${schema}
            uiSchema=${uiSchema}
            formData=${formData}
            onFormDataChange=${onFormDataChange}
            colors=${colors}
            editorHints=${editorHints}
            dataProfile=${dataProfile}
          />
          <${TieredVisualDesign}
            schema=${schema}
            uiSchema=${uiSchema}
            formData=${formData}
            colors=${colors}
            onFormDataChange=${onFormDataChange}
            fieldTiers=${fieldTiers}
            compositeWidgets=${compositeWidgets}
            seriesExcluded=${seriesExcludedFields}
            visualFields=${visualDesignFields}
            excludedFields=${editorHints?.excluded_fields}
            onOpenYaml=${onYamlToggle}
          />
        </section>

        <section
          class="editor-section"
          data-section="text"
          ref=${registerSection("text")}
        >
          <div class="editor-section-header">
            <h3 tabindex="-1">Text & Output</h3>
            <p>Chart narrative and output file name.</p>
          </div>
          <${MetadataSection}
            formData=${formData}
            onFormDataChange=${onFormDataChange}
          />
        </section>
      </div>

      <div
        class="resize-handle ${isResizing ? "active" : ""}"
        onMouseDown=${handleResizeStart}
      />

      <${PreviewPanel}
        buildFullConfig=${buildFullConfig}
        formData=${formData}
        dataConfig=${dataConfig}
        device=${previewDevice}
        onDeviceChange=${onPreviewDeviceChange}
        preflight=${preflight}
        renderTick=${renderTick}
      />
    </div>

    ${yamlOpen &&
    html`
      <${YamlPane}
        yamlText=${preflight?.yaml_preview}
        currentFile=${currentFile}
        lastEditedField=${lastEditedField}
        onClose=${onYamlClose}
        onReloadFromDisk=${onReloadFromDisk}
        showToast=${showToast}
      />
    `}

    ${toast && html`<${Toast} message=${toast.message} type=${toast.type} />`}
  `;
}
