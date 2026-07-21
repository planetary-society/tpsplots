/**
 * Unified series table for charts with correlated series: one row per series, owning
 * binding AND styling together (no more hopping between a binding editor and
 * a separate style table).
 *
 * Row layout is two-tier (a flat row doesn't fit the panel): the primary row
 * holds reorder + binding + label + color + remove; a per-row disclosure
 * holds linestyle/weight/marker/size/opacity. Left-axis (`y`) rows come
 * first, right-axis (`y_right`) rows after a divider — correlated arrays
 * index across the concatenation (see lib/seriesArrays.js). Moving a series
 * between axes is remove + re-add by design (no cross-axis index surgery).
 *
 * All writes go through lib/seriesArrays.js so reordering and removal
 * atomically permute every correlated style array with the binding.
 */
import { useCallback, useMemo } from "react";
import { html } from "../lib/html.js";

import {
  seriesValueAt,
  writeSeriesValue,
  numericSeriesDefault,
  permuteCorrelated,
  spliceCorrelated,
  normalizeBindings,
  bindingFieldValue,
} from "../lib/seriesArrays.js";
import { isNumericColumn } from "../lib/columnTypes.js";
import { decodeEscapes, encodeEscapes } from "../lib/escapedText.js";
import { stripTemplateBraces } from "./fields/templateRefUtils.js";
import { TemplateChipInput } from "./fields/TemplateChipInput.js";
import { MiniColorPicker } from "../widgets/MiniColorPicker.js";
import { LINESTYLE_OPTIONS } from "../widgets/lineStyleOptions.js";

const MARKER_OPTIONS = [
  { value: "", label: "—" },
  { value: "o", label: "●" },
  { value: "s", label: "■" },
  { value: "^", label: "▲" },
  { value: "D", label: "◆" },
  { value: "X", label: "✖" },
];

export function SeriesTable({
  formData,
  onFormDataChange,
  correlatedFields,
  colors,
  columns,
}) {
  const triggerField = correlatedFields?.trigger_field || "y";
  const secondaryField = correlatedFields?.secondary_trigger_field;
  const correlated = correlatedFields?.correlated || [];
  const tpsColors = useMemo(() => colors?.tps_colors || {}, [colors]);
  // Area perimeters default to no stroke, so 0 is a valid weight and the
  // stepping is finer; stroked series need a visible minimum.
  const allowsZeroLinewidth = formData?.type === "area";

  const leftBindings = useMemo(
    () => normalizeBindings(formData?.[triggerField]),
    [formData, triggerField]
  );
  const rightBindings = useMemo(
    () => (secondaryField ? normalizeBindings(formData?.[secondaryField]) : []),
    [formData, secondaryField]
  );
  const totalCount = leftBindings.length + rightBindings.length;

  const numericColumns = useMemo(
    () => (columns || []).filter(isNumericColumn),
    [columns]
  );
  const selectedColumns = useMemo(
    () =>
      new Set(
        [...leftBindings, ...rightBindings].map((item) => stripTemplateBraces(item)).filter(Boolean)
      ),
    [leftBindings, rightBindings]
  );

  // --- binding writes -----------------------------------------------------

  // Plain functions: nothing downstream is memoized, and each closes over
  // the current formData so a stale-closure useCallback would be a hazard.
  function commitBindings(axisField, nextBindings, base = formData) {
    const next = { ...base };
    const value = bindingFieldValue(nextBindings);
    if (value === undefined) {
      delete next[axisField];
    } else {
      next[axisField] = value;
    }
    onFormDataChange(next);
  }

  function updateBindingAt(axisField, bindings, index, text) {
    const next = [...bindings];
    next[index] = text;
    commitBindings(axisField, next);
  }

  function addSeries(axisField, bindings, token) {
    commitBindings(axisField, [...bindings, token ? `{{${token}}}` : ""]);
  }

  function removeSeriesAt(axisField, bindings, index) {
    const spliced = spliceCorrelated(formData, correlatedFields, axisField, index);
    const next = bindings.filter((_, i) => i !== index);
    commitBindings(axisField, next, spliced);
  }

  function toggleColumn(axisField, bindings, columnName) {
    const idx = bindings.findIndex((item) => stripTemplateBraces(item) === columnName);
    if (idx >= 0) {
      removeSeriesAt(axisField, bindings, idx);
      return;
    }
    addSeries(axisField, bindings, columnName);
  }

  function moveSeries(axisField, bindings, index, direction) {
    const target = index + direction;
    if (target < 0 || target >= bindings.length) return;
    // Permute every correlated style array first, then swap the binding on
    // top of the permuted formData so both land in one commit.
    const permuted = permuteCorrelated(formData, correlatedFields, axisField, index, target);
    const next = [...bindings];
    [next[index], next[target]] = [next[target], next[index]];
    commitBindings(axisField, next, permuted);
  }

  // --- style writes (concatenated index) ----------------------------------

  const handleStyleChange = useCallback(
    (concatIndex, fieldName, newValue) => {
      const nextArray = writeSeriesValue(
        formData[fieldName],
        concatIndex,
        totalCount,
        newValue,
        numericSeriesDefault(fieldName, formData?.type)
      );
      const next = { ...formData };
      if (nextArray === undefined) {
        delete next[fieldName];
      } else {
        next[fieldName] = nextArray;
      }
      onFormDataChange(next);
    },
    [formData, onFormDataChange, totalCount]
  );

  const has = useCallback((field) => correlated.includes(field), [correlated]);

  // --- rendering ----------------------------------------------------------

  const numberStyleField = (concatIndex, field, label, { min, max, step }) => html`
    <label class="series-style-field">
      <span>${label}</span>
      <input
        type="number"
        min=${min}
        max=${max}
        step=${step}
        value=${seriesValueAt(formData?.[field], concatIndex) ?? ""}
        onInput=${(e) =>
          handleStyleChange(
            concatIndex,
            field,
            e.target.value ? Number(e.target.value) : undefined
          )}
      />
    </label>
  `;

  const selectStyleField = (concatIndex, field, label, options) => html`
    <label class="series-style-field">
      <span>${label}</span>
      <select
        value=${seriesValueAt(formData?.[field], concatIndex) || ""}
        onChange=${(e) => handleStyleChange(concatIndex, field, e.target.value)}
      >
        ${options.map(
          (opt) => html`<option key=${opt.value} value=${opt.value}>${opt.label}</option>`
        )}
      </select>
    </label>
  `;

  const colorStyleField = (concatIndex, field, label) => html`
    <label class="series-style-field">
      <span>${label}</span>
      <${MiniColorPicker}
        value=${seriesValueAt(formData?.[field], concatIndex) || ""}
        onChange=${(v) => handleStyleChange(concatIndex, field, v)}
        tpsColors=${tpsColors}
      />
    </label>
  `;

  const renderRow = (axisField, bindings, index, concatIndex) => {
    const binding = bindings[index];
    return html`
      <div key=${`${axisField}-${index}`} class="series-row">
        <div class="series-row-main">
          <div class="series-row-move">
            <button
              type="button"
              class="series-move-btn"
              title="Move up"
              disabled=${index === 0}
              onClick=${() => moveSeries(axisField, bindings, index, -1)}
            >↑</button>
            <button
              type="button"
              class="series-move-btn"
              title="Move down"
              disabled=${index === bindings.length - 1}
              onClick=${() => moveSeries(axisField, bindings, index, 1)}
            >↓</button>
          </div>

          <${TemplateChipInput}
            className="series-row-binding"
            value=${binding}
            placeholder="{{Column Name}}"
            onInput=${(e) => updateBindingAt(axisField, bindings, index, e.target.value)}
          />

          ${has("labels") &&
          html`
            <input
              type="text"
              class="series-row-label"
              value=${encodeEscapes(seriesValueAt(formData?.labels, concatIndex) || "")}
              placeholder="Label"
              title=${'Type \\n for a line break'}
              onInput=${(e) => handleStyleChange(concatIndex, "labels", decodeEscapes(e.target.value))}
            />
          `}

          ${has("color") &&
          html`
            <${MiniColorPicker}
              value=${seriesValueAt(formData?.color, concatIndex) || ""}
              onChange=${(v) => handleStyleChange(concatIndex, "color", v)}
              tpsColors=${tpsColors}
            />
          `}

          <button
            type="button"
            class="series-remove-btn"
            title="Remove series"
            onClick=${() => removeSeriesAt(axisField, bindings, index)}
          >×</button>
        </div>

        <details class="series-row-style">
          <summary>Style</summary>
          <div class="series-row-style-grid">
            ${has("linestyle") &&
            selectStyleField(concatIndex, "linestyle", "Line", LINESTYLE_OPTIONS)}
            ${has("linewidth") &&
            numberStyleField(concatIndex, "linewidth", "Weight", {
              min: allowsZeroLinewidth ? 0 : 0.5,
              max: 8,
              step: allowsZeroLinewidth ? 0.25 : 0.5,
            })}
            ${has("edgecolor") && colorStyleField(concatIndex, "edgecolor", "Edge")}
            ${has("marker") && selectStyleField(concatIndex, "marker", "Marker", MARKER_OPTIONS)}
            ${has("markersize") &&
            numberStyleField(concatIndex, "markersize", "Size", { min: 1, max: 24, step: 1 })}
            ${has("alpha") &&
            numberStyleField(concatIndex, "alpha", "Opacity", { min: 0, max: 1, step: 0.1 })}
          </div>
        </details>
      </div>
    `;
  };

  const renderAxisGroup = (axisField, bindings, label, offset) => html`
    <div class="series-axis-group">
      <div class="series-axis-header">
        <h4>${label}</h4>
        <button
          type="button"
          class="series-add-btn"
          onClick=${() => addSeries(axisField, bindings)}
        >+ Add series</button>
      </div>
      ${bindings.length === 0 &&
      html`<p class="series-empty">No series yet — add one or pick a column below.</p>`}
      ${bindings.map((_, i) => renderRow(axisField, bindings, i, offset + i))}
      ${numericColumns.length > 0 &&
      html`
        <div class="binding-suggestions">
          ${numericColumns.map(
            (col) => html`
              <button
                key=${col.name}
                type="button"
                class=${`binding-suggestion ${selectedColumns.has(col.name) ? "binding-suggestion--selected" : ""}`}
                title="Data column"
                onClick=${() => toggleColumn(axisField, bindings, col.name)}
              >${col.name}</button>
            `
          )}
        </div>
      `}
    </div>
  `;

  return html`
    <div class="series-table">
      ${renderAxisGroup(triggerField, leftBindings, "Series", 0)}
      ${secondaryField &&
      (rightBindings.length > 0 || leftBindings.length > 0) &&
      html`
        <details class="series-right-axis" open=${rightBindings.length > 0 || undefined}>
          <summary>Right axis</summary>
          ${renderAxisGroup(secondaryField, rightBindings, "Right-axis series", leftBindings.length)}
        </details>
      `}
    </div>
  `;
}
