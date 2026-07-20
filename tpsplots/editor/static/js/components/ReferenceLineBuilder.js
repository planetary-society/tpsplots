/**
 * Composite reference line builder.
 *
 * Replaces 5+ individual hline_* array fields with a card-based UI
 * where each reference line shows properties in a 2-row layout.
 * Reuses MiniColorPicker and LINESTYLE_OPTIONS from the series editor
 * for consistent UX.
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";
import { useNumericText } from "../lib/numericText.js";
import { decodeEscapes, encodeEscapes } from "../lib/escapedText.js";

import { ChartForm } from "./ChartForm.js";
import { MiniColorPicker } from "../widgets/MiniColorPicker.js";
import { LINESTYLE_OPTIONS } from "../widgets/lineStyleOptions.js";

const DEFAULT_LINE = {
  value: 0,
  label: "",
  color: "Lunar Soil",
  style: "--",
  width: 1.0,
};

// Per-field pad value used when back-filling an array that is shorter than
// `hlines` (a YAML author may supply fewer labels/colors/etc. than lines).
// Padding with these defaults instead of `undefined` keeps committed arrays
// free of `null` cells — `undefined` JSON-serializes to `null`, which fails
// the Pydantic list validators (e.g. `hline_widths: list[float]`).
const FIELD_DEFAULTS = {
  hlines: DEFAULT_LINE.value,
  hline_labels: DEFAULT_LINE.label,
  hline_colors: DEFAULT_LINE.color,
  hline_styles: DEFAULT_LINE.style,
  hline_widths: DEFAULT_LINE.width,
};

function getArray(formData, field) {
  const val = formData?.[field];
  if (Array.isArray(val)) return val;
  if (val != null) return [val];
  return [];
}

/** Parse display text to a number, or `undefined` for empty/unparseable. */
function parseNum(text) {
  if (text === "") return undefined;
  const num = Number(text);
  return Number.isNaN(num) ? undefined : num;
}

/**
 * Number input for a numeric reference-line cell (Y value, width).
 *
 * Adapts the restore-on-blur pattern from fields/NumberField.js: it holds the
 * raw display text locally and commits ONLY parseable numbers. Crucially, it
 * never commits `undefined` — an empty or invalid box leaves the last valid
 * number in place in formData, so `hlines` / `hline_widths` can never gain a
 * `null` cell (which JSON-serializes from `undefined` and fails Pydantic's
 * `list[float]`, blocking preview/save). On blur, an empty/invalid box snaps
 * back to the committed value so the display never shows stale text.
 */
function RefLineNumberInput({ value, onCommit, className }) {
  // commitEmpty: false — empty/unparseable text commits nothing, so the last
  // valid number stays in formData and serialized arrays never gain nulls.
  // restoreOnBlur — an abandoned empty/invalid box snaps back to the
  // committed value rather than leaving orphaned text.
  const { raw, handleInput, handleBlur } = useNumericText({
    value,
    parse: parseNum,
    onCommit,
    commitEmpty: false,
    restoreOnBlur: true,
  });

  return html`
    <input
      type="text"
      inputmode="decimal"
      class=${className}
      value=${raw}
      onInput=${handleInput}
      onBlur=${handleBlur}
    />
  `;
}

export function ReferenceLineBuilder({
  formData,
  onFormDataChange,
  colors,
  config,
  schema,
  uiSchema,
}) {
  const globalFields = config?.global_fields || [];
  const tpsColors = useMemo(() => colors?.tps_colors || {}, [colors]);

  const hlines = getArray(formData, "hlines");
  const count = hlines.length;

  const updateField = useCallback(
    (index, fieldName, value) => {
      const arr = [...getArray(formData, fieldName)];
      // Back-fill gaps with the field's default (never `undefined`, which would
      // serialize to an interior `null` and fail Pydantic list validation).
      const pad = FIELD_DEFAULTS[fieldName] ?? "";
      while (arr.length <= index) arr.push(pad);
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

  // Global fields: strip ui:groups to render flat (avoids duplicate
  // "Reference Lines" collapsible wrapper inside this builder)
  const globalSet = useMemo(() => new Set(globalFields), [globalFields]);
  const globalUiSchema = useMemo(() => {
    if (!uiSchema) return {};
    // eslint-disable-next-line no-unused-vars
    const { "ui:groups": _groups, ...rest } = uiSchema;
    return rest;
  }, [uiSchema]);

  return html`
    <details class="refline-builder" open=${count > 0 || undefined}>
      <summary class="refline-summary">
        <span class="tier-arrow">\u25B8</span>
        Reference Lines
        ${count > 0 && html`<span class="tier-badge">${count}</span>`}
      </summary>

      <div class="refline-content">
        ${hlines.map(
          (hval, i) => html`
            <div key=${i} class="refline-card">
              <div class="refline-row1">
                <div class="refline-field">
                  <label class="refline-field-label">Y Value</label>
                  <${RefLineNumberInput}
                    className="refline-input"
                    value=${hval}
                    onCommit=${(num) => updateField(i, "hlines", num)}
                  />
                </div>
                <div class="refline-field refline-field-grow">
                  <label class="refline-field-label">Label</label>
                  <input
                    type="text"
                    class="refline-input"
                    value=${encodeEscapes(getArray(formData, "hline_labels")[i] || "")}
                    placeholder="Label text"
                    title=${'Type \\n for a line break'}
                    onInput=${(e) =>
                      updateField(i, "hline_labels", decodeEscapes(e.target.value))}
                  />
                </div>
                <button
                  type="button"
                  class="refline-remove-btn"
                  title="Remove line"
                  onClick=${() => removeLine(i)}
                >
                  \u00D7
                </button>
              </div>
              <div class="refline-row2">
                <div class="refline-field">
                  <label class="refline-field-label">Color</label>
                  <${MiniColorPicker}
                    value=${getArray(formData, "hline_colors")[i] || ""}
                    onChange=${(v) => updateField(i, "hline_colors", v)}
                    tpsColors=${tpsColors}
                  />
                </div>
                <div class="refline-field">
                  <label class="refline-field-label">Style</label>
                  <select
                    class="refline-select"
                    value=${getArray(formData, "hline_styles")[i] || "--"}
                    onChange=${(e) =>
                      updateField(i, "hline_styles", e.target.value)}
                  >
                    ${LINESTYLE_OPTIONS.map(
                      (opt) => html`
                        <option key=${opt.value} value=${opt.value}>
                          ${opt.label}
                        </option>
                      `
                    )}
                  </select>
                </div>
                <div class="refline-field">
                  <label class="refline-field-label">Width</label>
                  <${RefLineNumberInput}
                    className="refline-input refline-input-width"
                    value=${getArray(formData, "hline_widths")[i] ?? DEFAULT_LINE.width}
                    onCommit=${(num) => updateField(i, "hline_widths", num)}
                  />
                </div>
              </div>
            </div>
          `
        )}

        <button type="button" class="refline-add-btn" onClick=${addLine}>
          + Add Reference Line
        </button>

        ${globalFields.length > 0 &&
        count > 0 &&
        html`
          <div class="refline-global">
            <${ChartForm}
              schema=${schema}
              uiSchema=${globalUiSchema}
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
