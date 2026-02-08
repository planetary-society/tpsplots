/**
 * Composite reference line builder.
 *
 * Replaces 5+ individual hline_* array fields with a unified table
 * where each row represents one reference line with all its properties.
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

import { ChartForm } from "./ChartForm.js";

const STYLE_OPTIONS = [
  { value: "--", label: "dashed \u2013\u2013" },
  { value: "-", label: "solid \u2014" },
  { value: "-.", label: "dash-dot \u2013\u00B7" },
  { value: ":", label: "dotted \u00B7\u00B7\u00B7" },
];

const DEFAULT_LINE = {
  value: 0,
  label: "",
  color: "Lunar Soil",
  style: "--",
  width: 1.0,
};

function getArray(formData, field) {
  const val = formData?.[field];
  if (Array.isArray(val)) return val;
  if (val != null) return [val];
  return [];
}

export function ReferenceLineBuilder({
  formData,
  onFormDataChange,
  colors,
  config,
  schema,
  uiSchema,
}) {
  const fields = config?.fields || [];
  const globalFields = config?.global_fields || [];
  const tpsColors = useMemo(() => colors?.tps_colors || {}, [colors]);
  const colorEntries = useMemo(() => Object.entries(tpsColors), [tpsColors]);

  const hlines = getArray(formData, "hlines");
  const count = hlines.length;

  const updateField = useCallback(
    (index, fieldName, value) => {
      const arr = [...getArray(formData, fieldName)];
      while (arr.length <= index) arr.push(undefined);
      arr[index] = value;
      onFormDataChange({ ...formData, [fieldName]: arr });
    },
    [formData, onFormDataChange]
  );

  const addLine = useCallback(() => {
    onFormDataChange({
      ...formData,
      hlines: [...hlines, DEFAULT_LINE.value],
      hline_labels: [...getArray(formData, "hline_labels"), DEFAULT_LINE.label],
      hline_colors: [
        ...getArray(formData, "hline_colors"),
        DEFAULT_LINE.color,
      ],
      hline_styles: [
        ...getArray(formData, "hline_styles"),
        DEFAULT_LINE.style,
      ],
      hline_widths: [
        ...getArray(formData, "hline_widths"),
        DEFAULT_LINE.width,
      ],
    });
  }, [formData, onFormDataChange, hlines]);

  const removeLine = useCallback(
    (index) => {
      const removeAt = (field) => {
        const arr = getArray(formData, field).filter((_, i) => i !== index);
        return arr.length > 0 ? arr : undefined;
      };
      onFormDataChange({
        ...formData,
        hlines: removeAt("hlines"),
        hline_labels: removeAt("hline_labels"),
        hline_colors: removeAt("hline_colors"),
        hline_styles: removeAt("hline_styles"),
        hline_widths: removeAt("hline_widths"),
        hline_alpha: removeAt("hline_alpha"),
      });
    },
    [formData, onFormDataChange]
  );

  // Global fields rendered as a filtered ChartForm
  const globalSet = useMemo(() => new Set(globalFields), [globalFields]);

  return html`
    <details class="refline-builder" open=${count > 0 || undefined}>
      <summary class="refline-summary">
        <span class="tier-arrow">\u25B8</span>
        Reference Lines
        ${count > 0 &&
        html`<span class="tier-badge">${count}</span>`}
      </summary>

      <div class="refline-content">
        ${count > 0 &&
        html`
          <div class="refline-table">
            <div class="refline-header">
              <span class="refline-col refline-col-value">Y Value</span>
              <span class="refline-col refline-col-label">Label</span>
              <span class="refline-col refline-col-color">Color</span>
              <span class="refline-col refline-col-style">Style</span>
              <span class="refline-col refline-col-width">Width</span>
              <span class="refline-col refline-col-remove" />
            </div>

            ${hlines.map(
              (hval, i) => html`
                <div key=${i} class="refline-row">
                  <span class="refline-col refline-col-value">
                    <input
                      type="number"
                      class="refline-input"
                      value=${hval ?? ""}
                      step="any"
                      onInput=${(e) =>
                        updateField(
                          i,
                          "hlines",
                          e.target.value ? Number(e.target.value) : undefined
                        )}
                    />
                  </span>
                  <span class="refline-col refline-col-label">
                    <input
                      type="text"
                      class="refline-input"
                      value=${getArray(formData, "hline_labels")[i] || ""}
                      placeholder="Label"
                      onInput=${(e) =>
                        updateField(i, "hline_labels", e.target.value)}
                    />
                  </span>
                  <span class="refline-col refline-col-color">
                    <select
                      class="refline-select"
                      value=${getArray(formData, "hline_colors")[i] || ""}
                      onChange=${(e) =>
                        updateField(i, "hline_colors", e.target.value)}
                    >
                      <option value="">default</option>
                      ${colorEntries.map(
                        ([name]) => html`
                          <option key=${name} value=${name}>${name}</option>
                        `
                      )}
                    </select>
                  </span>
                  <span class="refline-col refline-col-style">
                    <select
                      class="refline-select"
                      value=${getArray(formData, "hline_styles")[i] || "--"}
                      onChange=${(e) =>
                        updateField(i, "hline_styles", e.target.value)}
                    >
                      ${STYLE_OPTIONS.map(
                        (opt) => html`
                          <option key=${opt.value} value=${opt.value}>
                            ${opt.label}
                          </option>
                        `
                      )}
                    </select>
                  </span>
                  <span class="refline-col refline-col-width">
                    <input
                      type="number"
                      class="refline-input refline-input-narrow"
                      value=${getArray(formData, "hline_widths")[i] ?? 1}
                      min="0.5"
                      max="5"
                      step="0.5"
                      onInput=${(e) =>
                        updateField(
                          i,
                          "hline_widths",
                          e.target.value ? Number(e.target.value) : undefined
                        )}
                    />
                  </span>
                  <span class="refline-col refline-col-remove">
                    <button
                      type="button"
                      class="refline-remove-btn"
                      title="Remove line"
                      onClick=${() => removeLine(i)}
                    >
                      \u00D7
                    </button>
                  </span>
                </div>
              `
            )}
          </div>
        `}

        <button
          type="button"
          class="refline-add-btn"
          onClick=${addLine}
        >
          + Add Reference Line
        </button>

        ${globalFields.length > 0 &&
        count > 0 &&
        html`
          <div class="refline-global">
            <${ChartForm}
              schema=${schema}
              uiSchema=${uiSchema}
              formData=${formData}
              colors=${colors}
              onFormDataChange=${onFormDataChange}
              includeFields=${globalSet}
            />
          </div>
        `}
      </div>
    </details>
  `;
}
