/**
 * Purpose-built editor for DataSourceConfig.calculate_inflation.
 */
import { useMemo, useState, useCallback } from "react";
import { html } from "../lib/html.js";

function normalizeConfig(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function normalizeColumns(value) {
  return Array.isArray(value) ? value.filter((col) => typeof col === "string" && col.trim() !== "") : [];
}

export function InflationConfigWidget({ value, onChange, options }) {
  const config = normalizeConfig(value);
  const enabled = value != null;
  const availableColumns = useMemo(
    () => (options?.availableColumns || []).map((col) => String(col)),
    [options]
  );

  const [newColumn, setNewColumn] = useState("");

  const commit = useCallback(
    (nextConfig) => {
      if (!enabled && Object.keys(nextConfig).length === 0) {
        onChange(undefined);
        return;
      }
      const cleaned = { ...nextConfig };
      cleaned.columns = normalizeColumns(cleaned.columns);
      if (cleaned.columns.length === 0) cleaned.columns = [];
      if (!cleaned.type) cleaned.type = "nnsi";
      if (!cleaned.fiscal_year_column) cleaned.fiscal_year_column = "Fiscal Year";
      if (cleaned.target_year === "" || cleaned.target_year == null) delete cleaned.target_year;
      onChange(cleaned);
    },
    [onChange, enabled]
  );

  const setEnabled = useCallback(
    (checked) => {
      if (!checked) {
        onChange(undefined);
        return;
      }
      commit({
        columns: normalizeColumns(config.columns),
        type: config.type || "nnsi",
        fiscal_year_column: config.fiscal_year_column || "Fiscal Year",
        target_year: config.target_year,
      });
    },
    [config, onChange, commit]
  );

  const setField = useCallback(
    (fieldName, nextValue) => {
      const next = {
        columns: normalizeColumns(config.columns),
        type: config.type || "nnsi",
        fiscal_year_column: config.fiscal_year_column || "Fiscal Year",
        target_year: config.target_year,
      };
      if (nextValue === undefined || nextValue === null || nextValue === "") {
        delete next[fieldName];
      } else {
        next[fieldName] = nextValue;
      }
      commit(next);
    },
    [config, commit]
  );

  const columns = normalizeColumns(config.columns);
  const selected = new Set(columns);

  const toggleColumn = useCallback(
    (columnName) => {
      const nextColumns = selected.has(columnName)
        ? columns.filter((col) => col !== columnName)
        : [...columns, columnName];
      setField("columns", nextColumns);
    },
    [selected, columns, setField]
  );

  const addColumn = useCallback(() => {
    const name = newColumn.trim();
    if (!name || selected.has(name)) return;
    setField("columns", [...columns, name]);
    setNewColumn("");
  }, [newColumn, selected, columns, setField]);

  return html`
    <div class="inflation-config-widget">
      <label class="data-params-checkbox">
        <input
          type="checkbox"
          checked=${enabled}
          onChange=${(e) => setEnabled(e.target.checked)}
        />
        <span>Apply inflation adjustment</span>
      </label>

      ${enabled &&
      html`
        <div class="inflation-config-panel">
          <div class="data-params-section">
            <h5 class="data-params-title">Columns</h5>
            <div class="binding-suggestions">
              ${availableColumns.map(
                (col) => html`
                  <button
                    key=${col}
                    type="button"
                    class=${`binding-suggestion ${
                      selected.has(col) ? "binding-suggestion--selected" : ""
                    }`}
                    onClick=${() => toggleColumn(col)}
                  >
                    ${col}
                  </button>
                `
              )}
            </div>

            <div class="data-params-inline">
              <input
                type="text"
                class="field-input"
                value=${newColumn}
                placeholder="Add column manually"
                onInput=${(e) => setNewColumn(e.target.value)}
                onKeyDown=${(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addColumn();
                  }
                }}
              />
              <button
                type="button"
                class="btn btn-secondary"
                onClick=${addColumn}
                disabled=${!newColumn.trim()}
              >
                Add
              </button>
            </div>
          </div>

          <div class="data-params-inline">
            <label class="data-params-field">
              <span>Inflation index</span>
              <select
                class="field-input"
                value=${config.type || "nnsi"}
                onChange=${(e) => setField("type", e.target.value)}
              >
                <option value="nnsi">nnsi</option>
                <option value="gdp">gdp</option>
              </select>
            </label>

            <label class="data-params-field">
              <span>Fiscal year column</span>
              <input
                type="text"
                class="field-input"
                value=${config.fiscal_year_column || "Fiscal Year"}
                list="inflation-columns"
                onInput=${(e) => setField("fiscal_year_column", e.target.value || "Fiscal Year")}
              />
            </label>
          </div>

          <label class="data-params-field">
            <span>Target year (optional)</span>
            <input
              type="number"
              class="field-input"
              value=${config.target_year ?? ""}
              placeholder="Auto-calculate if empty"
              min="1900"
              max="2200"
              onInput=${(e) => setField("target_year", e.target.value ? Number(e.target.value) : undefined)}
            />
          </label>
        </div>
      `}

      <datalist id="inflation-columns">
        ${availableColumns.map((col) => html`<option key=${col} value=${col} />`)}
      </datalist>
    </div>
  `;
}
