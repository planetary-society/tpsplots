/**
 * Visual legend builder widget.
 *
 * Replaces the generic UnionField for the `legend` config field with a
 * purpose-built control: toggle + 3x3 position grid + font size + border.
 *
 * Produces: false (off), true (default on), or a dict like
 *   { loc: "upper right", fontsize: "small", frameon: false }
 */
import { useMemo, useCallback } from "react";
import { html } from "../lib/html.js";

const POSITIONS = [
  ["upper left", "upper center", "upper right"],
  ["center left", "center", "center right"],
  ["lower left", "lower center", "lower right"],
];

// Short labels for the 3x3 grid buttons
const POS_LABELS = {
  "upper left": "UL",
  "upper center": "UC",
  "upper right": "UR",
  "center left": "CL",
  center: "C",
  "center right": "CR",
  "lower left": "LL",
  "lower center": "LC",
  "lower right": "LR",
};

const FONTSIZE_OPTIONS = [
  { value: "", label: "Default" },
  { value: "x-small", label: "X-Small" },
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

export function LegendBuilderWidget({ value, onChange }) {
  const isOff = value === false;
  const isDict = value != null && typeof value === "object" && !Array.isArray(value);
  const config = isDict ? value : {};

  const currentLoc = config.loc || "";
  const currentFontsize = config.fontsize || "";
  const currentFrameon = config.frameon !== false; // default true

  const handleToggle = useCallback(
    (checked) => {
      onChange(checked ? true : false);
    },
    [onChange]
  );

  const handlePositionClick = useCallback(
    (pos) => {
      const next = { ...config, loc: pos };
      onChange(next);
    },
    [config, onChange]
  );

  const handleFontsizeChange = useCallback(
    (size) => {
      const next = { ...config };
      if (size) {
        next.fontsize = size;
      } else {
        delete next.fontsize;
      }
      // Collapse to true if only default values remain
      if (Object.keys(next).length === 0) {
        onChange(true);
      } else {
        onChange(next);
      }
    },
    [config, onChange]
  );

  const handleFrameonChange = useCallback(
    (checked) => {
      const next = { ...config, frameon: checked };
      // If frameon is true (default), remove it to keep dict clean
      if (checked) delete next.frameon;
      if (Object.keys(next).length === 0) {
        onChange(true);
      } else {
        onChange(next);
      }
    },
    [config, onChange]
  );

  // Show the grid position as a visual description
  const posDescription = useMemo(() => {
    if (!currentLoc) return "Default";
    return currentLoc
      .split(" ")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }, [currentLoc]);

  return html`
    <div class="legend-builder">
      <label class="legend-toggle">
        <input
          type="checkbox"
          checked=${!isOff}
          onChange=${(e) => handleToggle(e.target.checked)}
        />
        <span>Show Legend</span>
      </label>

      ${!isOff &&
      html`
        <div class="legend-options">
          <div class="legend-position-section">
            <span class="legend-option-label">Position: ${posDescription}</span>
            <div class="legend-position-grid">
              ${POSITIONS.map(
                (row, ri) => html`
                  <div key=${ri} class="legend-position-row">
                    ${row.map(
                      (pos) => html`
                        <button
                          key=${pos}
                          type="button"
                          class="legend-pos-cell ${currentLoc === pos
                            ? "active"
                            : ""}"
                          onClick=${() => handlePositionClick(pos)}
                          title=${pos}
                        >
                          ${POS_LABELS[pos]}
                        </button>
                      `
                    )}
                  </div>
                `
              )}
            </div>
          </div>

          <div class="legend-extra-row">
            <label class="legend-fontsize-label">
              Size
              <select
                class="legend-fontsize-select"
                value=${currentFontsize}
                onChange=${(e) => handleFontsizeChange(e.target.value)}
              >
                ${FONTSIZE_OPTIONS.map(
                  (opt) => html`
                    <option key=${opt.value} value=${opt.value}>
                      ${opt.label}
                    </option>
                  `
                )}
              </select>
            </label>

            <label class="legend-frameon-label">
              <input
                type="checkbox"
                checked=${currentFrameon}
                onChange=${(e) => handleFrameonChange(e.target.checked)}
              />
              Border
            </label>
          </div>
        </div>
      `}
    </div>
  `;
}
