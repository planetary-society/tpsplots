/**
 * Data bindings: one card per binding, where the card IS the input —
 * an editable template-chip field with status and column suggestions in the
 * same surface (no duplicate form field below). Line/scatter y-series use
 * the unified SeriesTable (binding + styling per row) instead of cards.
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

import { ChartForm } from "./ChartForm.js";
import { SeriesTable } from "./SeriesTable.js";
import { TemplateChipInput } from "./fields/TemplateChipInput.js";
import { parseTemplateReferences, stripTemplateBraces } from "./fields/templateRefUtils.js";
import { formatFieldLabel } from "./fields/fieldLabelUtils.js";
import { classifyColumn } from "../lib/columnTypes.js";

function suggestionsForField(fieldName, columns, contextKeys) {
  const lower = String(fieldName).toLowerCase();
  const decorated = columns.map(classifyColumn);

  // Controller context bindings (e.g. pie_data) are not dataframe columns.
  if (lower === "pie_data") {
    return contextKeys.map((name) => ({ name: String(name), source: "context" }));
  }

  if (lower === "x") {
    const dateFirst = [...decorated].sort((a, b) => Number(b.isDate) - Number(a.isDate));
    return dateFirst.slice(0, 6).map((col) => ({ name: col.name, source: "column" }));
  }

  if (lower.includes("value") || lower === "y" || lower === "y_right" || lower === "start_values" || lower === "end_values") {
    const numericFirst = [...decorated].sort((a, b) => Number(b.isNumeric) - Number(a.isNumeric));
    return numericFirst.slice(0, 6).map((col) => ({ name: col.name, source: "column" }));
  }

  return decorated.slice(0, 6).map((col) => ({ name: col.name, source: "column" }));
}

// Tooltip listing the columns/context keys a reference could resolve to.
function availableColumnsTitle(referenceNames) {
  if (referenceNames.length === 0) return undefined;
  const shown = referenceNames.slice(0, 15);
  const suffix = referenceNames.length > 15 ? ", …" : "";
  return `Available: ${shown.join(", ")}${suffix}`;
}

// Returns { status, label, title? }. `status` is the internal state key that
// drives the `status-*` card CSS class; `label` is the user-facing copy.
function bindingStatus(fieldName, formData, referenceNames) {
  const value = formData?.[fieldName];
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) {
    return { status: "unbound", label: "Not set" };
  }

  const values = Array.isArray(value) ? value : [value];
  const refs = values
    .filter((v) => typeof v === "string")
    .flatMap((v) => parseTemplateReferences(v));

  if (refs.length > 0 && referenceNames.length > 0) {
    const missingRef = refs.find((ref) => !referenceNames.includes(stripTemplateBraces(ref)));
    if (missingRef) {
      return {
        status: "invalid-ref",
        label: `'${missingRef}' not in data`,
        title: availableColumnsTitle(referenceNames),
      };
    }
    return { status: "bound", label: "Linked" };
  }

  if (refs.length > 0) return { status: "pending", label: "Load data to check" };
  // A literal (non-{{ref}}) value — e.g. a fixed label list.
  return { status: "bound", label: "Fixed value" };
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
  const columns = dataProfile?.columns || [];
  const contextKeys = (dataProfile?.context_keys || []).map((key) => String(key));
  const columnNames = columns.map((col) => String(col.name));
  const referenceNames = useMemo(
    () => [...new Set([...columnNames, ...contextKeys])],
    [columnNames, contextKeys]
  );

  const isSeriesBindingMode = (formData?.type === "line" || formData?.type === "scatter") && primary.includes("y");
  const cardFields = isSeriesBindingMode ? primary.filter((field) => field !== "y" && field !== "y_right") : primary;

  const assignSingleField = useCallback(
    (fieldName, token) => {
      onFormDataChange({ ...formData, [fieldName]: `{{${token}}}` });
    },
    [formData, onFormDataChange]
  );

  const setFieldText = useCallback(
    (fieldName, text) => {
      const next = { ...formData };
      if (text === "") {
        delete next[fieldName];
      } else {
        next[fieldName] = text;
      }
      onFormDataChange(next);
    },
    [formData, onFormDataChange]
  );

  return html`
    <div class="binding-area">
      ${cardFields.length > 0 &&
      html`
        <div class="binding-cards">
          ${cardFields.map((fieldName) => {
            const { status, label, title } = bindingStatus(fieldName, formData, referenceNames);
            const suggestions = suggestionsForField(fieldName, columns, contextKeys);
            const value = formData?.[fieldName];
            const isArrayValue = Array.isArray(value);

            return html`
              <div key=${fieldName} class="binding-card status-${status}" data-field=${fieldName}>
                <div class="binding-card-header">
                  <strong>${formatFieldLabel(fieldName, schema?.properties?.[fieldName])}</strong>
                  <span class="binding-status" title=${title}>${label}</span>
                </div>
                ${isArrayValue
                  ? html`
                      <${ChartForm}
                        schema=${schema}
                        uiSchema=${uiSchema}
                        formData=${formData}
                        colors=${colors}
                        onFormDataChange=${onFormDataChange}
                        includeFields=${includeSetFor(fieldName)}
                      />
                    `
                  : html`
                      <${TemplateChipInput}
                        className="binding-card-input"
                        value=${value ?? ""}
                        placeholder="{{Column Name}} or a fixed value"
                        onInput=${(e) => setFieldText(fieldName, e.target.value)}
                      />
                    `}
                ${suggestions.length > 0 &&
                html`
                  <div class="binding-suggestions">
                    ${suggestions.map(
                      (suggestion) => html`
                        <button
                          key=${`${fieldName}-${suggestion.name}`}
                          type="button"
                          class="binding-suggestion"
                          onClick=${() => assignSingleField(fieldName, suggestion.name)}
                          title=${suggestion.source === "context" ? "Controller context value" : "Data column"}
                        >
                          ${suggestion.name}
                        </button>
                      `
                    )}
                  </div>
                `}
              </div>
            `;
          })}
        </div>
      `}

      ${isSeriesBindingMode &&
      html`
        <${SeriesTable}
          formData=${formData}
          onFormDataChange=${onFormDataChange}
          correlatedFields=${editorHints?.series_correlated_fields}
          colors=${colors}
          columns=${columns}
          showLinestyle=${formData?.type !== "scatter"}
        />
      `}
    </div>
  `;
}

// Stable per-field include sets so ChartForm's useMemo cache is not busted
// by a fresh Set each render (house referential-stability rule).
const CARD_INCLUDE_SETS = new Map();

function includeSetFor(fieldName) {
  if (!CARD_INCLUDE_SETS.has(fieldName)) {
    CARD_INCLUDE_SETS.set(fieldName, new Set([fieldName]));
  }
  return CARD_INCLUDE_SETS.get(fieldName);
}
