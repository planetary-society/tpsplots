/**
 * Main editor layout: header + split pane (form | preview).
 */
import { useState, useCallback, createElement } from "react";
import htm from "htm";

import { Header } from "./Header.js";
import { ChartForm } from "./ChartForm.js";
import { MetadataSection } from "./MetadataSection.js";
import { PreviewPanel } from "./PreviewPanel.js";
import { Toast } from "./Toast.js";

const html = htm.bind(createElement);

export function EditorLayout(props) {
  const {
    chartType, chartTypes, schema, uiSchema, formData, dataConfig,
    currentFile, colors, toast,
    onChartTypeChange, onFormDataChange, onDataConfigChange,
    onFileChange, buildFullConfig, showToast,
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
    />

    <div class="editor-layout" style=${{ gridTemplateColumns: `${formWidth}px 6px 1fr` }}>
      <div class="form-panel">
        <${MetadataSection}
          formData=${formData}
          onFormDataChange=${onFormDataChange}
        />

        <${ChartForm}
          schema=${schema}
          uiSchema=${uiSchema}
          formData=${formData}
          colors=${colors}
          onFormDataChange=${onFormDataChange}
        />
      </div>

      <div
        class="resize-handle ${isResizing ? "active" : ""}"
        onMouseDown=${handleResizeStart}
      />

      <${PreviewPanel}
        buildFullConfig=${buildFullConfig}
        formData=${formData}
        dataConfig=${dataConfig}
      />
    </div>

    ${toast && html`<${Toast} message=${toast.message} type=${toast.type} />`}
  `;
}
