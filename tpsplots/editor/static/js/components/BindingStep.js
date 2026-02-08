/**
 * Guided Data Bindings step with suggested column mapping.
 */
import { createElement } from "react";
import htm from "htm";

import { ChartForm } from "./ChartForm.js";
import { parseTemplateReferences } from "./fields/templateRefUtils.js";
import { formatFieldLabel } from "./fields/fieldLabelUtils.js";

const html = htm.bind(createElement);

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

function bindingStatus(fieldName, formData, columnNames) {
  const value = formData?.[fieldName];
  if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) {
    return "unbound";
  }
  if (typeof value === "string") {
    const refs = parseTemplateReferences(value);
    if (refs.length > 0) {
      const missing = refs.some((ref) => !columnNames.includes(ref.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "")));
      return missing ? "invalid-ref" : "bound";
    }
  }
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
  const columnNames = columns.map((c) => String(c.name));

  const assignField = (fieldName, colName) => {
    onFormDataChange({ ...formData, [fieldName]: `{{${colName}}}` });
  };

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
                      (col) => html`
                        <button
                          key=${`${fieldName}-${col.name}`}
                          type="button"
                          class="binding-suggestion"
                          onClick=${() => assignField(fieldName, col.name)}
                        >
                          ${col.name}
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
        includeFields=${new Set(primary)}
      />
    </section>
  `;
}

