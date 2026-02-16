/**
 * Guided Data Bindings step with suggested mapping cards.
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

import { ChartForm } from "./ChartForm.js";
import { SeriesBindingEditor } from "./SeriesBindingEditor.js";
import { parseTemplateReferences } from "./fields/templateRefUtils.js";
import { formatFieldLabel } from "./fields/fieldLabelUtils.js";

function classifyColumn(col) {
  const name = String(col?.name || "");
  const dtype = String(col?.dtype || "").toLowerCase();
  const lower = name.toLowerCase();
  return {
    name,
    isDate: dtype.includes("date") || dtype.includes("time") || lower.includes("year"),
    isNumeric:
      dtype.includes("int") ||
      dtype.includes("float") ||
      dtype.includes("double") ||
      dtype.includes("number"),
  };
}

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

function stripBraces(ref) {
  return String(ref).replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "");
}

function bindingStatus(fieldName, formData, referenceNames) {
  const value = formData?.[fieldName];
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) {
    return "unbound";
  }

  const values = Array.isArray(value) ? value : [value];
  const refs = values
    .filter((v) => typeof v === "string")
    .flatMap((v) => parseTemplateReferences(v));

  if (refs.length > 0 && referenceNames.length > 0) {
    const missing = refs.some((ref) => !referenceNames.includes(stripBraces(ref)));
    return missing ? "invalid-ref" : "bound";
  }

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
  const columns = dataProfile?.columns || [];
  const contextKeys = (dataProfile?.context_keys || []).map((key) => String(key));
  const columnNames = columns.map((col) => String(col.name));
  const referenceNames = useMemo(
    () => [...new Set([...columnNames, ...contextKeys])],
    [columnNames, contextKeys]
  );

  const isSeriesBindingMode = (formData?.type === "line" || formData?.type === "scatter") && primary.includes("y");
  const hasYRight = isSeriesBindingMode && primary.includes("y_right");
  const cardFields = isSeriesBindingMode ? primary.filter((field) => field !== "y" && field !== "y_right") : primary;
  const primarySet = useMemo(() => new Set(cardFields), [cardFields]);

  const assignSingleField = useCallback(
    (fieldName, token) => {
      onFormDataChange({ ...formData, [fieldName]: `{{${token}}}` });
    },
    [formData, onFormDataChange]
  );

  return html`
    <section class="guided-step">
      <div class="guided-step-header">
        <h3>Data Bindings</h3>
        <p>Assign your processed data columns to chart inputs. Changes to column names or types in Data Setup are reflected here.</p>
      </div>

      ${isSeriesBindingMode &&
      html`
        <${SeriesBindingEditor}
          fieldName="y"
          label="Y Series (Left Axis)"
          formData=${formData}
          onFormDataChange=${onFormDataChange}
          columns=${columns}
        />
      `}

      ${hasYRight &&
      html`
        <${SeriesBindingEditor}
          fieldName="y_right"
          label="Right Y-Axis Series"
          formData=${formData}
          onFormDataChange=${onFormDataChange}
          columns=${columns}
        />
      `}

      ${cardFields.length > 0 &&
      html`
        <div class="binding-cards">
          ${cardFields.map((fieldName) => {
            const status = bindingStatus(fieldName, formData, referenceNames);
            const suggestions = suggestionsForField(fieldName, columns, contextKeys);

            return html`
              <div key=${fieldName} class="binding-card status-${status}">
                <div class="binding-card-header">
                  <strong>${formatFieldLabel(fieldName, schema?.properties?.[fieldName])}</strong>
                  <span class="binding-status">${status.replace("-", " ")}</span>
                </div>
                <div class="binding-current">
                  ${formData?.[fieldName] != null && formData?.[fieldName] !== ""
                    ? String(formData[fieldName])
                    : "Not set"}
                </div>
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

      <${ChartForm}
        schema=${schema}
        uiSchema=${uiSchema}
        formData=${formData}
        colors=${colors}
        onFormDataChange=${onFormDataChange}
        includeFields=${primarySet}
      />

    </section>
  `;
}
