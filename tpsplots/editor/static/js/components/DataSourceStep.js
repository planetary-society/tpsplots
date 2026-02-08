/**
 * Guided Data Source & Preparation step.
 */
import { useMemo, createElement } from "react";
import htm from "htm";

import { SchemaForm } from "./SchemaForm.js";

const html = htm.bind(createElement);

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
          uiSchema=${dataUiSchema || {}}
          formData=${dataConfig || {}}
          onChange=${onDataConfigChange}
          hiddenFields=${new Set()}
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

