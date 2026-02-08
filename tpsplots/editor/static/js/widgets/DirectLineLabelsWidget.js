/**
 * Direct line labels widget for line/scatter charts.
 *
 * Supports bool|object values:
 * - false/undefined: disabled
 * - true: enabled with defaults
 * - object: enabled with explicit options
 */
import { useCallback } from "react";
import { html } from "../lib/html.js";

const POSITION_OPTIONS = [
  "auto",
  "right",
  "left",
  "top",
  "bottom",
  "above",
  "below",
];

function isPlainObject(value) {
  return value != null && typeof value === "object" && !Array.isArray(value);
}

export function DirectLineLabelsWidget({ value, onChange }) {
  const enabled = value === true || isPlainObject(value);
  const config = isPlainObject(value) ? value : {};
  const rawEndpoint = config.end_point;
  const endpointEnabled = rawEndpoint === true || isPlainObject(rawEndpoint);
  const endpointConfig = isPlainObject(rawEndpoint) ? rawEndpoint : {};

  const commitConfig = useCallback(
    (nextConfig) => {
      const keys = Object.keys(nextConfig);
      onChange(keys.length > 0 ? nextConfig : true);
    },
    [onChange]
  );

  const setEnabled = useCallback(
    (checked) => {
      if (!checked) {
        onChange(false);
        return;
      }
      if (isPlainObject(value)) {
        onChange(value);
        return;
      }
      onChange(true);
    },
    [onChange, value]
  );

  const setConfigField = useCallback(
    (field, nextValue) => {
      const nextConfig = { ...config };
      if (nextValue === undefined || nextValue === null || nextValue === "") {
        delete nextConfig[field];
      } else {
        nextConfig[field] = nextValue;
      }
      commitConfig(nextConfig);
    },
    [config, commitConfig]
  );

  const setEndpointEnabled = useCallback(
    (checked) => {
      if (!checked) {
        setConfigField("end_point", undefined);
        return;
      }
      if (endpointEnabled && rawEndpoint != null) {
        setConfigField("end_point", rawEndpoint);
        return;
      }
      setConfigField("end_point", { marker: "o", size: 8 });
    },
    [endpointEnabled, rawEndpoint, setConfigField]
  );

  const setEndpointField = useCallback(
    (field, nextValue) => {
      const nextEndpoint = { ...endpointConfig };
      if (nextValue === undefined || nextValue === null || nextValue === "") {
        delete nextEndpoint[field];
      } else {
        nextEndpoint[field] = nextValue;
      }
      setConfigField("end_point", Object.keys(nextEndpoint).length > 0 ? nextEndpoint : true);
    },
    [endpointConfig, setConfigField]
  );

  return html`
    <div class="direct-line-labels-widget">
      <label class="direct-line-labels-toggle">
        <input
          type="checkbox"
          checked=${enabled}
          onChange=${(e) => setEnabled(e.target.checked)}
        />
        <span>Enable direct line labels</span>
      </label>

      ${enabled &&
      html`
        <div class="direct-line-labels-panel">
          <div class="direct-line-labels-row">
            <label class="direct-line-labels-field">
              <span>Position</span>
              <select
                value=${config.position || "auto"}
                onChange=${(e) =>
                  setConfigField("position", e.target.value === "auto" ? undefined : e.target.value)}
              >
                ${POSITION_OPTIONS.map(
                  (opt) => html`<option key=${opt} value=${opt}>${opt}</option>`
                )}
              </select>
            </label>

            <label class="direct-line-labels-field direct-line-labels-field--narrow">
              <span>Font size</span>
              <input
                type="number"
                min="6"
                step="1"
                value=${config.fontsize ?? ""}
                placeholder="auto"
                onInput=${(e) =>
                  setConfigField(
                    "fontsize",
                    e.target.value ? Number(e.target.value) : undefined
                  )}
              />
            </label>
          </div>

          <label class="direct-line-labels-checkbox">
            <input
              type="checkbox"
              checked=${config.bbox !== false}
              onChange=${(e) => setConfigField("bbox", e.target.checked ? undefined : false)}
            />
            <span>Label background box</span>
          </label>

          <div class="direct-line-labels-endpoint">
            <label class="direct-line-labels-checkbox">
              <input
                type="checkbox"
                checked=${endpointEnabled}
                onChange=${(e) => setEndpointEnabled(e.target.checked)}
              />
              <span>Endpoint marker</span>
            </label>

            ${endpointEnabled &&
            html`
              <div class="direct-line-labels-row">
                <label class="direct-line-labels-field direct-line-labels-field--narrow">
                  <span>Marker</span>
                  <input
                    type="text"
                    value=${endpointConfig.marker || "o"}
                    onInput=${(e) => setEndpointField("marker", e.target.value || undefined)}
                  />
                </label>

                <label class="direct-line-labels-field direct-line-labels-field--narrow">
                  <span>Size</span>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value=${endpointConfig.size ?? ""}
                    placeholder="auto"
                    onInput=${(e) =>
                      setEndpointField("size", e.target.value ? Number(e.target.value) : undefined)}
                  />
                </label>
              </div>
            `}
          </div>
        </div>
      `}
    </div>
  `;
}
