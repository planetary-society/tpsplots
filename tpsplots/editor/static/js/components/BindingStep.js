/**
 * Guided Data Bindings step with suggested column mapping.
 *
 * Single-value fields (e.g. x): click a suggestion to replace the binding.
 * Multi-value fields (e.g. y on line/scatter): click suggestions to toggle
 * columns on/off, stored as an array when 2+ are selected.
 */
import { useCallback, useMemo } from "react";
import { html } from "../lib/html.js";

import { ChartForm } from "./ChartForm.js";
import { SeriesEditor } from "./SeriesEditor.js";
import { parseTemplateReferences } from "./fields/templateRefUtils.js";
import { formatFieldLabel } from "./fields/fieldLabelUtils.js";

function classifyColumn(col) {
  const name = String(col?.name || "");
  const dtype = String(col?.dtype || "").toLowerCase();
  const lower = name.toLowerCase();
  return {
    isDate: dtype.includes("date") || dtype.includes("time") || lower.includes("year"),
    isNumeric:
      dtype.includes("int") || dtype.includes("float") || dtype.includes("double") || dtype.includes("number"),
  };
}

function suggestionsForField(fieldName, columns) {
  const lower = String(fieldName).toLowerCase();
  const decorated = columns.map((c) => ({ ...c, meta: classifyColumn(c) }));

  if (lower === "x") {
    const dateFirst = [...decorated].sort((a, b) => Number(b.meta.isDate) - Number(a.meta.isDate));
    return dateFirst.slice(0, 6);
  }

  if (
    lower.includes("value") ||
    lower === "y" ||
    lower === "start_values" ||
    lower === "end_values"
  ) {
    const numericFirst = [...decorated].sort(
      (a, b) => Number(b.meta.isNumeric) - Number(a.meta.isNumeric)
    );
    return numericFirst.slice(0, 6);
  }

  return decorated.slice(0, 6);
}

function stripBraces(ref) {
  return ref.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "");
}

/** Return true when this field is the multi-series trigger (e.g. "y"). */
function isMultiValueField(fieldName, editorHints) {
  const correlated = editorHints?.series_correlated_fields;
  return correlated?.trigger_field === fieldName;
}

/** Extract the column names currently bound for a field. */
function getBoundColumns(fieldName, formData) {
  const value = formData?.[fieldName];
  if (value == null || value === "") return [];
  if (Array.isArray(value)) {
    return value
      .filter((v) => typeof v === "string")
      .map((v) => stripBraces(v))
      .filter(Boolean);
  }
  if (typeof value === "string") {
    const refs = parseTemplateReferences(value);
    return refs.map((r) => stripBraces(r)).filter(Boolean);
  }
  return [];
}

function bindingStatus(fieldName, formData, columnNames) {
  const value = formData?.[fieldName];
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) {
    return "unbound";
  }

  // Collect all template refs from string or array-of-strings values
  const values = Array.isArray(value) ? value : [value];
  const refs = values
    .filter((v) => typeof v === "string")
    .flatMap((v) => parseTemplateReferences(v));

  if (refs.length > 0 && columnNames.length > 0) {
    const missing = refs.some((ref) => !columnNames.includes(stripBraces(ref)));
    return missing ? "invalid-ref" : "bound";
  }

  // Refs found but no columns loaded yet — don't flag as invalid
  if (refs.length > 0) return "pending";

  return "bound";
}

export function BindingStep({
  formData,
  onFormDataChange,
  schema,
  uiSchema,
  colors,
  editorHints,
  dataProfile,
}) {
  const primary = editorHints?.primary_binding_fields || [];
  const seriesCorrelated = editorHints?.series_correlated_fields || null;
  const primarySet = useMemo(() => new Set(primary), [primary]);
  const columns = dataProfile?.columns || [];
  const columnNames = columns.map((c) => String(c.name));

  /** Single-value: replace the field with one column reference. */
  const assignSingleField = useCallback(
    (fieldName, colName) => {
      onFormDataChange({ ...formData, [fieldName]: `{{${colName}}}` });
    },
    [formData, onFormDataChange]
  );

  /** Multi-value: toggle a column on/off in the field's array. */
  const toggleMultiField = useCallback(
    (fieldName, colName) => {
      const current = formData?.[fieldName];
      const ref = `{{${colName}}}`;

      // Normalize current value to an array of refs
      let currentRefs = [];
      if (Array.isArray(current)) {
        currentRefs = [...current];
      } else if (typeof current === "string" && current.trim() !== "") {
        const parsed = parseTemplateReferences(current);
        currentRefs = parsed.length > 0 ? [...parsed] : [current];
      }

      // Toggle: remove if already present, add otherwise
      const idx = currentRefs.findIndex((r) => stripBraces(r) === colName);
      if (idx >= 0) {
        currentRefs.splice(idx, 1);
      } else {
        currentRefs.push(ref);
      }

      // Normalize output: 0 → delete, 1 → string, 2+ → array
      if (currentRefs.length === 0) {
        const next = { ...formData };
        delete next[fieldName];
        onFormDataChange(next);
      } else if (currentRefs.length === 1) {
        onFormDataChange({ ...formData, [fieldName]: currentRefs[0] });
      } else {
        onFormDataChange({ ...formData, [fieldName]: currentRefs });
      }
    },
    [formData, onFormDataChange]
  );

  return html`
    <section class="guided-step">
      <div class="guided-step-header">
        <h3>Data Bindings</h3>
        <p>Map required chart fields to your resolved source columns.</p>
      </div>

      ${primary.length > 0 &&
      html`
        <div class="binding-cards">
          ${primary.map((fieldName) => {
            const status = bindingStatus(fieldName, formData, columnNames);
            const suggestions = suggestionsForField(fieldName, columns);
            const isMulti = isMultiValueField(fieldName, editorHints);
            const boundCols = isMulti ? getBoundColumns(fieldName, formData) : [];
            const boundSet = new Set(boundCols);

            return html`
              <div key=${fieldName} class="binding-card status-${status}">
                <div class="binding-card-header">
                  <strong>${formatFieldLabel(fieldName, schema?.properties?.[fieldName])}</strong>
                  <span class="binding-status">${status.replace("-", " ")}</span>
                </div>

                ${isMulti
                  ? html`
                      <div class="binding-chips">
                        ${boundCols.length === 0
                          ? html`<span class="binding-current-empty">No columns selected</span>`
                          : boundCols.map(
                              (col) => html`
                                <span key=${col} class="binding-chip">
                                  <span class="binding-chip-label">${col}</span>
                                  <button
                                    type="button"
                                    class="binding-chip-remove"
                                    onClick=${() => toggleMultiField(fieldName, col)}
                                    title="Remove ${col}"
                                  >
                                    \u00d7
                                  </button>
                                </span>
                              `
                            )}
                      </div>
                      ${suggestions.length > 0 &&
                      html`
                        <div class="binding-suggestions">
                          ${suggestions.map(
                            (col) => html`
                              <button
                                key=${`${fieldName}-${col.name}`}
                                type="button"
                                class=${`binding-suggestion ${
                                  boundSet.has(col.name) ? "binding-suggestion--selected" : ""
                                }`}
                                onClick=${() => toggleMultiField(fieldName, col.name)}
                              >
                                ${col.name}
                              </button>
                            `
                          )}
                        </div>
                      `}
                    `
                  : html`
                      <div class="binding-current">
                        ${formData?.[fieldName] != null && formData?.[fieldName] !== ""
                          ? String(formData[fieldName])
                          : "Not set"}
                      </div>
                      ${suggestions.length > 0 &&
                      html`
                        <div class="binding-suggestions">
                          ${suggestions.map(
                            (col) => html`
                              <button
                                key=${`${fieldName}-${col.name}`}
                                type="button"
                                class="binding-suggestion"
                                onClick=${() => assignSingleField(fieldName, col.name)}
                              >
                                ${col.name}
                              </button>
                            `
                          )}
                        </div>
                      `}
                    `}
              </div>
            `;
          })}
        </div>
      `}

      <${ChartForm}
        schema=${schema}
        uiSchema=${uiSchema}
        formData=${formData}
        colors=${colors}
        onFormDataChange=${onFormDataChange}
        includeFields=${primarySet}
      />

      ${seriesCorrelated &&
      html`
        <${SeriesEditor}
          formData=${formData}
          onFormDataChange=${onFormDataChange}
          correlatedFields=${seriesCorrelated}
          colors=${colors}
        />
      `}
    </section>
  `;
}
