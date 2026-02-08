/**
 * Main editor layout: header + split pane (form | preview).
 */
import { useState, useCallback, useMemo } from "react";
import { html } from "../lib/html.js";

import { Header } from "./Header.js";
import { ChartForm } from "./ChartForm.js";
import { TieredVisualDesign } from "./TieredVisualDesign.js";
import { MetadataSection } from "./MetadataSection.js";
import { PreviewPanel } from "./PreviewPanel.js";
import { ValidationSummary } from "./ValidationSummary.js";
import { DataSourceStep } from "./DataSourceStep.js";
import { BindingStep } from "./BindingStep.js";
import { Toast } from "./Toast.js";

const STEPS = [
  { id: 1, key: "data_source_and_preparation", label: "1. Data Source & Prep" },
  { id: 2, key: "data_bindings", label: "2. Data Bindings" },
  { id: 3, key: "visual_design", label: "3. Visual Design" },
  { id: 4, key: "annotation_output", label: "4. Annotation & Output" },
];

function statusLabel(status) {
  if (status === "complete") return "Complete";
  if (status === "error") return "Needs attention";
  if (status === "in_progress") return "In progress";
  return "Not started";
}

export function EditorLayout(props) {
  const {
    chartType, chartTypes, schema, uiSchema, formData, dataConfig,
    currentFile, colors, toast,
    editorHints, preflight, stepStatus, activeStep,
    dataSchema, dataUiSchema, dataProfile, dataProfileStatus,
    previewDevice, renderTick, unsavedChanges,
    onChartTypeChange, onFormDataChange, onDataConfigChange,
    onFileChange, onStepChange, onPreviewDeviceChange,
    onRunDataProfile, onSaved, buildFullConfig, showToast,
  } = props;

  // Resize state
  const [formWidth, setFormWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);

  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    setIsResizing(true);
    const startX = e.clientX;
    const startWidth = formWidth;

    const onMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      const newWidth = Math.max(280, Math.min(600, startWidth + delta));
      setFormWidth(newWidth);
    };

    const onUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [formWidth]);

  const visualDesignFields = useMemo(
    () => new Set(editorHints?.step_field_map?.visual_design || []),
    [editorHints]
  );

  // Detect multi-series mode: when trigger field (y) is an array with 2+ items,
  // the series editor in Step 2 handles correlated fields — exclude them from Step 3.
  const seriesCorrelated = editorHints?.series_correlated_fields;
  const isMultiSeries = useMemo(() => {
    if (!seriesCorrelated) return false;
    const trigger = formData?.[seriesCorrelated.trigger_field];
    return Array.isArray(trigger) && trigger.length >= 2;
  }, [seriesCorrelated, formData]);

  const seriesExcludedFields = useMemo(() => {
    if (!isMultiSeries || !seriesCorrelated?.correlated) return null;
    return seriesCorrelated.correlated;
  }, [isMultiSeries, seriesCorrelated]);

  const fieldTiers = editorHints?.field_tiers;
  const compositeWidgets = editorHints?.composite_widgets;
  const hasTiers = fieldTiers && (fieldTiers.essential?.length > 0 || fieldTiers.common?.length > 0);

  const dataReady = stepStatus?.data_source_and_preparation === "complete";
  const toggleStep = useCallback(
    (stepId, isOpen) => {
      onStepChange(isOpen ? null : stepId);
    },
    [onStepChange]
  );

  const renderStepContent = (stepId) => {
    if (stepId === 1) {
      return html`
        <${DataSourceStep}
          dataSchema=${dataSchema}
          dataUiSchema=${dataUiSchema}
          dataConfig=${dataConfig}
          onDataConfigChange=${onDataConfigChange}
          onTestSource=${onRunDataProfile}
          profile=${dataProfile}
          profileStatus=${dataProfileStatus}
        />
      `;
    }

    if (stepId === 2) {
      const guidance = editorHints?.guidance;
      return html`
        ${guidance &&
        html`
          <details class="guidance-panel">
            <summary class="guidance-summary">Quick Start: ${chartType} chart</summary>
            <p class="guidance-desc">${guidance.description}</p>
            <ol class="guidance-steps">
              ${guidance.workflow?.map(
                (step, i) => html`<li key=${i}>${step}</li>`
              )}
            </ol>
            ${guidance.tip &&
            html`<p class="guidance-tip">${guidance.tip}</p>`}
          </details>
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
      `;
    }

    if (stepId === 3) {
      return html`
        <section class="guided-step">
          <div class="guided-step-header">
            <h3>Visual Design</h3>
            <p>Tune styling, scales, legends, and axis behavior.</p>
          </div>
          ${hasTiers
            ? html`
                <${TieredVisualDesign}
                  schema=${schema}
                  uiSchema=${uiSchema}
                  formData=${formData}
                  colors=${colors}
                  onFormDataChange=${onFormDataChange}
                  fieldTiers=${fieldTiers}
                  compositeWidgets=${compositeWidgets}
                  seriesExcluded=${seriesExcludedFields}
                />
              `
            : html`
                <${ChartForm}
                  schema=${schema}
                  uiSchema=${uiSchema}
                  formData=${formData}
                  colors=${colors}
                  onFormDataChange=${onFormDataChange}
                  includeFields=${visualDesignFields}
                />
              `}
        </section>
      `;
    }

    return html`
      <section class="guided-step">
        <div class="guided-step-header">
          <h3>Annotation & Output</h3>
          <p>Finalize chart narrative and output metadata.</p>
        </div>
        <${MetadataSection}
          formData=${formData}
          onFormDataChange=${onFormDataChange}
        />
      </section>
    `;
  };

  return html`
    <${Header}
      chartType=${chartType}
      chartTypes=${chartTypes}
      currentFile=${currentFile}
      onChartTypeChange=${onChartTypeChange}
      onFormDataChange=${onFormDataChange}
      onDataConfigChange=${onDataConfigChange}
      onFileChange=${onFileChange}
      buildFullConfig=${buildFullConfig}
      showToast=${showToast}
      dataConfig=${dataConfig}
      onSaved=${onSaved}
      unsavedChanges=${unsavedChanges}
      preflight=${preflight}
    />

    <div class="editor-layout" style=${{ gridTemplateColumns: `${formWidth}px 6px 1fr` }}>
      <div class="form-panel">
        <div class="step-accordion">
          ${STEPS.map((step) => {
            const status = stepStatus?.[step.key] || "not_started";
            const isOpen = activeStep === step.id;
            const disabled = step.id > 1 && !dataReady;
            return html`
              <section key=${step.key} class="step-accordion-item ${isOpen ? "is-open" : ""}">
                <button
                  type="button"
                  class="step-nav-item ${isOpen ? "active" : ""} status-${status}"
                  onClick=${() => !disabled && toggleStep(step.id, isOpen)}
                  disabled=${disabled}
                  aria-expanded=${isOpen}
                  aria-pressed=${isOpen}
                  title=${disabled ? "Complete Data Source & Prep first" : statusLabel(status)}
                >
                  <span class="step-nav-label">${step.label}</span>
                  <span class="step-nav-state">${statusLabel(status)}</span>
                </button>
                <div class="step-panel ${isOpen ? "is-open" : ""}" aria-hidden=${!isOpen}>
                  <div class="step-panel-inner">
                    ${isOpen && html`<${ValidationSummary} preflight=${preflight} />`}
                    ${renderStepContent(step.id)}
                  </div>
                </div>
              </section>
            `;
          })}
        </div>
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

    ${toast && html`<${Toast} message=${toast.message} type=${toast.type} />`}
  `;
}
