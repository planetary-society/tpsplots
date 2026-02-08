/**
 * Main editor layout: header + split pane (form | preview).
 */
import { useState, useCallback, createElement } from "react";
import htm from "htm";

import { Header } from "./Header.js";
import { ChartForm } from "./ChartForm.js";
import { MetadataSection } from "./MetadataSection.js";
import { PreviewPanel } from "./PreviewPanel.js";
import { StepNavigator } from "./StepNavigator.js";
import { ValidationSummary } from "./ValidationSummary.js";
import { DataSourceStep } from "./DataSourceStep.js";
import { BindingStep } from "./BindingStep.js";
import { Toast } from "./Toast.js";

const html = htm.bind(createElement);

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
        <${StepNavigator}
          activeStep=${activeStep}
          onStepChange=${onStepChange}
          stepStatus=${stepStatus}
        />

        <${ValidationSummary} preflight=${preflight} />

        ${activeStep === 1 &&
        html`
          <${DataSourceStep}
            dataSchema=${dataSchema}
            dataUiSchema=${dataUiSchema}
            dataConfig=${dataConfig}
            onDataConfigChange=${onDataConfigChange}
            onTestSource=${onRunDataProfile}
            profile=${dataProfile}
            profileStatus=${dataProfileStatus}
          />
        `}

        ${activeStep === 2 &&
        html`
          <${BindingStep}
            schema=${schema}
            uiSchema=${uiSchema}
            formData=${formData}
            onFormDataChange=${onFormDataChange}
            colors=${colors}
            editorHints=${editorHints}
            dataProfile=${dataProfile}
          />
        `}

        ${activeStep === 3 &&
        html`
          <section class="guided-step">
            <div class="guided-step-header">
              <h3>Visual Design</h3>
              <p>Tune styling, scales, legends, and axis behavior.</p>
            </div>
            <${ChartForm}
              schema=${schema}
              uiSchema=${uiSchema}
              formData=${formData}
              colors=${colors}
              onFormDataChange=${onFormDataChange}
              includeFields=${new Set(editorHints?.step_field_map?.visual_design || [])}
            />
          </section>
        `}

        ${activeStep === 4 &&
        html`
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
        `}
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
