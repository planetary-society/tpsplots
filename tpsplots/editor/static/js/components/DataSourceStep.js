/**
 * Guided Data Source & Preparation step.
 */
import { useMemo, useRef, useCallback } from "react";
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
  const profileColumns = useMemo(() => profile?.columns || [], [profile]);
  const columnNames = useMemo(
    () => profileColumns.map((col) => String(col.name)),
    [profileColumns]
  );
  const dialogRef = useRef(null);

  const openDialog = useCallback(() => {
    dialogRef.current?.showModal();
  }, []);

  const closeDialog = useCallback(() => {
    dialogRef.current?.close();
  }, []);

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
          availableColumns: profileColumns,
        },
      },
      calculate_inflation: {
        ...(dataUiSchema.calculate_inflation || {}),
        "ui:options": {
          ...(dataUiSchema.calculate_inflation?.["ui:options"] || {}),
          availableColumns: columnNames,
        },
      },
    };
  }, [dataUiSchema, profileColumns, columnNames]);

  return html`
    <section class="guided-step">
      <div class="guided-step-header">
        <h3>Data Source & Preparation</h3>
        <p>Load your data source, then configure which columns are available and how they're transformed.</p>
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
        <button
          type="button"
          class="btn btn-secondary"
          disabled=${!profile || sampleRows.length === 0}
          onClick=${openDialog}
        >
          View Data
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
            <span><strong>Columns:</strong> ${profileColumns.length}</span>
          </div>

          ${(profile.warnings || []).length > 0 &&
          html`
            <ul class="profile-warnings">
              ${profile.warnings.map((w, idx) => html`<li key=${idx}>${w}</li>`)}
            </ul>
          `}

          ${profileColumns.length > 0 &&
          html`
            <div class="profile-columns">
              ${profileColumns.map(
                (col) => html`<span key=${col.name} class="profile-column-pill">${col.name} (${col.dtype})</span>`
              )}
            </div>
          `}
        </div>
      `}

      <dialog ref=${dialogRef} class="data-table-dialog">
        <div class="data-table-dialog-header">
          <h4>Data Preview</h4>
          <span class="data-table-dialog-meta">
            Showing ${Math.min(sampleRows.length, profile?.row_count ?? 0)} of ${profile?.row_count ?? 0} rows
          </span>
          <button type="button" class="btn btn-secondary" onClick=${closeDialog}>Close</button>
        </div>
        ${sampleRows.length > 0 &&
        html`
          <div class="data-table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  ${profileColumns.map(
                    (col) => html`
                      <th key=${col.name}>
                        <span class="data-table-col-name">${col.name}</span>
                        <span class="data-table-col-dtype">${col.dtype}</span>
                      </th>
                    `
                  )}
                </tr>
              </thead>
              <tbody>
                ${sampleRows.map(
                  (row, i) => html`
                    <tr key=${i}>
                      ${profileColumns.map(
                        (col) => html`
                          <td key=${col.name}>
                            ${row[col.name] != null ? String(row[col.name]) : ""}
                          </td>
                        `
                      )}
                    </tr>
                  `
                )}
              </tbody>
            </table>
          </div>
        `}
      </dialog>
    </section>
  `;
}
