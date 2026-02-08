/**
 * Guided Data Source & Preparation step.
 */
import { useMemo } from "react";
import { html } from "../lib/html.js";

import { SchemaForm } from "./SchemaForm.js";
import { DataParamsWidget } from "../widgets/DataParamsWidget.js";
import { InflationConfigWidget } from "../widgets/InflationConfigWidget.js";

const EMPTY_HIDDEN = new Set();

export function DataSourceStep({
  dataSchema,
  dataUiSchema,
  dataConfig,
  onDataConfigChange,
  onTestSource,
  profile,
  profileStatus,
}) {
  const canTestSource = !!dataConfig?.source;
  const sampleRows = useMemo(() => profile?.sample_rows || [], [profile]);
  const availableColumns = useMemo(
    () => (profile?.columns || []).map((col) => String(col.name)),
    [profile]
  );

  const widgets = useMemo(
    () => ({ dataParams: DataParamsWidget, inflationConfig: InflationConfigWidget }),
    []
  );

  const enhancedUiSchema = useMemo(() => {
    if (!dataUiSchema) return {};
    return {
      ...dataUiSchema,
      params: {
        ...(dataUiSchema.params || {}),
        "ui:options": {
          ...(dataUiSchema.params?.["ui:options"] || {}),
          availableColumns,
        },
      },
      calculate_inflation: {
        ...(dataUiSchema.calculate_inflation || {}),
        "ui:options": {
          ...(dataUiSchema.calculate_inflation?.["ui:options"] || {}),
          availableColumns,
        },
      },
    };
  }, [dataUiSchema, availableColumns]);

  return html`
    <section class="guided-step">
      <div class="guided-step-header">
        <h3>Data Source & Preparation</h3>
        <p>Set your source first, then validate it before chart bindings.</p>
      </div>

      <div class="data-step-actions">
        <button
          type="button"
          class="btn btn-secondary"
          disabled=${!canTestSource || profileStatus === "loading"}
          onClick=${onTestSource}
        >
          ${profileStatus === "loading" ? "Testing Source\u2026" : "Test Source"}
        </button>
      </div>

      ${dataSchema &&
      html`
        <${SchemaForm}
          schema=${dataSchema}
          uiSchema=${enhancedUiSchema}
          formData=${dataConfig || {}}
          onChange=${onDataConfigChange}
          widgets=${widgets}
          hiddenFields=${EMPTY_HIDDEN}
        />
      `}

      ${profile &&
      html`
        <div class="data-profile-card">
          <div class="profile-meta">
            <span><strong>Source kind:</strong> ${profile.source_kind || "unknown"}</span>
            <span><strong>Rows:</strong> ${profile.row_count ?? 0}</span>
            <span><strong>Columns:</strong> ${(profile.columns || []).length}</span>
          </div>

          ${(profile.warnings || []).length > 0 &&
          html`
            <ul class="profile-warnings">
              ${profile.warnings.map((w, idx) => html`<li key=${idx}>${w}</li>`)}
            </ul>
          `}

          ${(profile.columns || []).length > 0 &&
          html`
            <div class="profile-columns">
              ${profile.columns.map(
                (col) => html`<span key=${col.name} class="profile-column-pill">${col.name} (${col.dtype})</span>`
              )}
            </div>
          `}

          ${sampleRows.length > 0 &&
          html`
            <details class="profile-sample">
              <summary>Preview sample rows</summary>
              <pre>${JSON.stringify(sampleRows, null, 2)}</pre>
            </details>
          `}
        </div>
      `}
    </section>
  `;
}
