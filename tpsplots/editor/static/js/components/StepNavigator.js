/**
 * Guided step navigator for editor workflow.
 */
import { createElement } from "react";
import htm from "htm";

const html = htm.bind(createElement);

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

export function StepNavigator({ activeStep, onStepChange, stepStatus = {} }) {
  const dataReady = stepStatus.data_source_and_preparation === "complete";

  return html`
    <nav class="step-nav" aria-label="Editor workflow steps">
      ${STEPS.map((step) => {
        const status = stepStatus[step.key] || "not_started";
        const disabled = step.id > 1 && !dataReady;
        return html`
          <button
            key=${step.key}
            type="button"
            class="step-nav-item ${activeStep === step.id ? "active" : ""} status-${status}"
            onClick=${() => !disabled && onStepChange(activeStep === step.id ? null : step.id)}
            disabled=${disabled}
            aria-pressed=${activeStep === step.id}
            title=${disabled ? "Complete Data Source & Prep first" : statusLabel(status)}
          >
            <span class="step-nav-label">${step.label}</span>
            <span class="step-nav-state">${statusLabel(status)}</span>
          </button>
        `;
      })}
    </nav>
  `;
}
