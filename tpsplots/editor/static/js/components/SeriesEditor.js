/**
 * Series-aware editor for multi-series line/scatter charts.
 *
 * When the trigger field (y) is an array with 2+ entries, this replaces
 * the individual color/labels/linestyle/marker fields with a unified
 * table where each row represents one series.
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

import { MiniColorPicker } from "../widgets/MiniColorPicker.js";
import { LINESTYLE_OPTIONS } from "../widgets/lineStyleOptions.js";

const MARKER_OPTIONS = [
  { value: "", label: "\u2014" },
  { value: "o", label: "\u25CF" },
  { value: "s", label: "\u25A0" },
  { value: "^", label: "\u25B2" },
  { value: "D", label: "\u25C6" },
  { value: "X", label: "\u2716" },
];

function stripBraces(ref) {
  if (typeof ref !== "string") return String(ref);
  return ref.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "");
}

export function SeriesEditor({
  formData,
  onFormDataChange,
  correlatedFields,
  colors,
}) {
  const triggerField = correlatedFields?.trigger_field || "y";
  const correlated = correlatedFields?.correlated || [];
  const yValue = formData?.[triggerField];
  const series = Array.isArray(yValue) ? yValue : [];

  const tpsColors = useMemo(() => colors?.tps_colors || {}, [colors]);

  const handleFieldChange = useCallback(
    (seriesIndex, fieldName, newValue) => {
      const currentArray = Array.isArray(formData[fieldName])
        ? [...formData[fieldName]]
        : [];
      // Pad array to match series length
      while (currentArray.length < series.length) {
        currentArray.push(undefined);
      }
      // For numbers: preserve 0, only clear on truly empty
      currentArray[seriesIndex] =
        newValue !== undefined && newValue !== null && newValue !== ""
          ? newValue
          : undefined;
      // Trim trailing undefineds
      while (currentArray.length > 0 && currentArray[currentArray.length - 1] == null) {
        currentArray.pop();
      }
      // If empty after trim, remove the field entirely
      if (currentArray.length === 0) {
        const next = { ...formData };
        delete next[fieldName];
        onFormDataChange(next);
        return;
      }
      // For numeric array fields, fill interior gaps with defaults so
      // Pydantic doesn't reject null inside list[float]
      const NUMERIC_DEFAULTS = { linewidth: 1.5, markersize: 6, alpha: 1.0 };
      const numDefault = NUMERIC_DEFAULTS[fieldName];
      if (numDefault !== undefined) {
        for (let j = 0; j < currentArray.length; j++) {
          if (currentArray[j] == null) currentArray[j] = numDefault;
        }
      }
      onFormDataChange({ ...formData, [fieldName]: currentArray });
    },
    [formData, onFormDataChange, series.length]
  );

  // Don't render for single series or no series
  if (series.length < 2) return null;

  // Determine which correlated fields are actually in the schema
  const hasColor = correlated.includes("color");
  const hasLabels = correlated.includes("labels");
  const hasLinestyle = correlated.includes("linestyle");
  const hasLinewidth = correlated.includes("linewidth");
  const hasMarker = correlated.includes("marker");
  const hasMarkersize = correlated.includes("markersize");
  const hasAlpha = correlated.includes("alpha");

  return html`
    <div class="series-editor">
      <div class="series-editor-header">
        <h4 class="series-editor-title">Series Configuration</h4>
        <span class="series-editor-count">${series.length} series</span>
      </div>

      <div class="series-editor-list">
        ${series.map(
          (s, i) => html`
            <div key=${i} class="series-card">
              <div class="series-card-name" title=${stripBraces(s)}>
                ${stripBraces(s)}
              </div>
              <div class="series-card-controls">
                ${hasColor &&
                html`
                  <div class="series-ctrl">
                    <span class="series-ctrl-label">Color</span>
                    <${MiniColorPicker}
                      value=${Array.isArray(formData.color)
                        ? formData.color[i]
                        : i === 0
                          ? formData.color
                          : ""}
                      onChange=${(v) => handleFieldChange(i, "color", v)}
                      tpsColors=${tpsColors}
                    />
                  </div>
                `}

                ${hasLabels &&
                html`
                  <div class="series-ctrl series-ctrl-label-field">
                    <span class="series-ctrl-label">Label</span>
                    <input
                      type="text"
                      class="series-input"
                      value=${Array.isArray(formData.labels)
                        ? formData.labels[i] || ""
                        : ""}
                      placeholder="Label"
                      onInput=${(e) =>
                        handleFieldChange(i, "labels", e.target.value)}
                    />
                  </div>
                `}

                ${hasLinestyle &&
                html`
                  <div class="series-ctrl">
                    <span class="series-ctrl-label">Style</span>
                    <select
                      class="series-select"
                      value=${Array.isArray(formData.linestyle)
                        ? formData.linestyle[i] || ""
                        : ""}
                      onChange=${(e) =>
                        handleFieldChange(i, "linestyle", e.target.value)}
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
                `}

                ${hasLinewidth &&
                html`
                  <div class="series-ctrl series-ctrl-narrow">
                    <span class="series-ctrl-label">Weight</span>
                    <input
                      type="number"
                      class="series-input series-input-narrow"
                      value=${Array.isArray(formData.linewidth)
                        ? formData.linewidth[i] ?? ""
                        : ""}
                      placeholder="px"
                      min="0.5"
                      max="8"
                      step="0.5"
                      onInput=${(e) =>
                        handleFieldChange(
                          i,
                          "linewidth",
                          e.target.value ? Number(e.target.value) : undefined
                        )}
                    />
                  </div>
                `}

                ${hasMarker &&
                html`
                  <div class="series-ctrl series-ctrl-narrow">
                    <span class="series-ctrl-label">Marker</span>
                    <select
                      class="series-select"
                      value=${Array.isArray(formData.marker)
                        ? formData.marker[i] || ""
                        : ""}
                      onChange=${(e) =>
                        handleFieldChange(i, "marker", e.target.value)}
                    >
                      ${MARKER_OPTIONS.map(
                        (opt) => html`
                          <option key=${opt.value} value=${opt.value}>
                            ${opt.label}
                          </option>
                        `
                      )}
                    </select>
                  </div>
                `}

                ${hasMarkersize &&
                html`
                  <div class="series-ctrl series-ctrl-narrow">
                    <span class="series-ctrl-label">Marker Size</span>
                    <input
                      type="number"
                      class="series-input series-input-narrow"
                      value=${Array.isArray(formData.markersize)
                        ? formData.markersize[i] ?? ""
                        : formData.markersize ?? ""}
                      placeholder="px"
                      min="1"
                      max="24"
                      step="1"
                      onInput=${(e) =>
                        handleFieldChange(
                          i,
                          "markersize",
                          e.target.value ? Number(e.target.value) : undefined
                        )}
                    />
                  </div>
                `}

                ${hasAlpha &&
                html`
                  <div class="series-ctrl series-ctrl-narrow">
                    <span class="series-ctrl-label">Opacity</span>
                    <input
                      type="number"
                      class="series-input series-input-narrow"
                      value=${Array.isArray(formData.alpha)
                        ? formData.alpha[i] ?? ""
                        : formData.alpha ?? ""}
                      min="0"
                      max="1"
                      step="0.1"
                      onInput=${(e) =>
                        handleFieldChange(
                          i,
                          "alpha",
                          e.target.value ? Number(e.target.value) : undefined
                        )}
                    />
                  </div>
                `}
              </div>
            </div>
          `
        )}
      </div>
    </div>
  `;
}
