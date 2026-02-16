/**
 * Dedicated multi-series binding editor for line/scatter y-series.
 *
 * Keeps bindings as:
 * - undefined when empty
 * - string for one series
 * - array for two or more series
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

import { TemplateChipInput } from "./fields/TemplateChipInput.js";

function templateRef(columnName) {
  return `{{${columnName}}}`;
}

function stripTemplate(ref) {
  if (typeof ref !== "string") return "";
  return ref.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "");
}

function normalizeBindings(value) {
  if (Array.isArray(value)) return value.filter((item) => typeof item === "string");
  if (typeof value === "string" && value.trim() !== "") return [value];
  return [];
}

function commitBindings(fieldName, nextBindings, formData, onFormDataChange) {
  const cleaned = nextBindings
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);

  const next = { ...formData };
  if (cleaned.length === 0) {
    delete next[fieldName];
  } else if (cleaned.length === 1) {
    next[fieldName] = cleaned[0];
  } else {
    next[fieldName] = cleaned;
  }
  onFormDataChange(next);
}

export function SeriesBindingEditor({
  fieldName = "y",
  label,
  formData,
  onFormDataChange,
  columns,
}) {
  const headerLabel = label || (fieldName === "y_right" ? "Right Y-Axis Series" : "Y Series");
  const bindings = useMemo(() => normalizeBindings(formData?.[fieldName]), [formData, fieldName]);
  const numericColumns = useMemo(
    () =>
      (columns || []).filter((col) => {
        const dtype = String(col?.dtype || "").toLowerCase();
        return (
          dtype.includes("int") ||
          dtype.includes("float") ||
          dtype.includes("double") ||
          dtype.includes("number")
        );
      }),
    [columns]
  );
  const selected = useMemo(
    () => new Set(bindings.map((item) => stripTemplate(item)).filter(Boolean)),
    [bindings]
  );

  const addEmpty = useCallback(() => {
    commitBindings(fieldName, [...bindings, ""], formData, onFormDataChange);
  }, [bindings, fieldName, formData, onFormDataChange]);

  const updateAt = useCallback(
    (index, value) => {
      const next = [...bindings];
      next[index] = value;
      commitBindings(fieldName, next, formData, onFormDataChange);
    },
    [bindings, fieldName, formData, onFormDataChange]
  );

  const removeAt = useCallback(
    (index) => {
      const next = bindings.filter((_, idx) => idx !== index);
      commitBindings(fieldName, next, formData, onFormDataChange);
    },
    [bindings, fieldName, formData, onFormDataChange]
  );

  const move = useCallback(
    (index, direction) => {
      const target = index + direction;
      if (target < 0 || target >= bindings.length) return;
      const next = [...bindings];
      [next[index], next[target]] = [next[target], next[index]];
      commitBindings(fieldName, next, formData, onFormDataChange);
    },
    [bindings, fieldName, formData, onFormDataChange]
  );

  const toggleSuggestion = useCallback(
    (columnName) => {
      const ref = templateRef(columnName);
      const idx = bindings.findIndex((item) => stripTemplate(item) === columnName);
      if (idx >= 0) {
        const next = bindings.filter((_, currentIdx) => currentIdx !== idx);
        commitBindings(fieldName, next, formData, onFormDataChange);
        return;
      }
      commitBindings(fieldName, [...bindings, ref], formData, onFormDataChange);
    },
    [bindings, fieldName, formData, onFormDataChange]
  );

  return html`
    <div class="series-binding-editor">
      <div class="series-binding-header">
        <h4>${headerLabel}</h4>
        <button type="button" class="series-binding-add" onClick=${addEmpty}>+ Add series</button>
      </div>

      <div class="series-binding-list">
        ${bindings.length === 0 &&
        html`<p class="series-binding-empty">No series selected yet.</p>`}

        ${bindings.map(
          (binding, index) => html`
            <div key=${`${binding}-${index}`} class="series-binding-row">
              <span class="series-binding-index">${index + 1}</span>
              <${TemplateChipInput}
                className="series-binding-input"
                value=${binding}
                placeholder="{{Column Name}}"
                onInput=${(e) => updateAt(index, e.target.value)}
              />
              <div class="series-binding-actions">
                <button
                  type="button"
                  class="series-binding-action"
                  title="Move up"
                  disabled=${index === 0}
                  onClick=${() => move(index, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  class="series-binding-action"
                  title="Move down"
                  disabled=${index === bindings.length - 1}
                  onClick=${() => move(index, 1)}
                >
                  ↓
                </button>
                <button
                  type="button"
                  class="series-binding-action series-binding-action--danger"
                  title="Remove series"
                  onClick=${() => removeAt(index)}
                >
                  ×
                </button>
              </div>
            </div>
          `
        )}
      </div>

      ${numericColumns.length > 0 &&
      html`
        <div class="series-binding-suggestions">
          <span class="series-binding-suggestions-label">Quick add numeric columns</span>
          <div class="binding-suggestions">
            ${numericColumns.map(
              (col) => html`
                <button
                  key=${col.name}
                  type="button"
                  class=${`binding-suggestion ${
                    selected.has(col.name) ? "binding-suggestion--selected" : ""
                  }`}
                  onClick=${() => toggleSuggestion(col.name)}
                >
                  ${col.name}
                </button>
              `
            )}
          </div>
        </div>
      `}
    </div>
  `;
}
