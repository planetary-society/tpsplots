/**
 * Purpose-built editor for DataSourceConfig.params.
 *
 * Shows a column configuration grid (include, cast per column) plus
 * separate sections for renames, currency cleaning, and fiscal year.
 */
import { useMemo, useState, useCallback } from "react";
import { html } from "../lib/html.js";

function normalizeColumns(value) {
  return Array.isArray(value) ? value.filter((col) => typeof col === "string" && col.trim() !== "") : [];
}

function normalizeObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function isPlainObject(value) {
  return value != null && typeof value === "object" && !Array.isArray(value);
}

const CAST_OPTIONS = ["", "str", "int", "float", "datetime", "bool"];

export function DataParamsWidget({ value, onChange, options }) {
  const params = normalizeObject(value);

  // availableColumns is now full column objects [{name, dtype}, ...]
  const profileColumns = useMemo(
    () => (options?.availableColumns || []).map((col) =>
      typeof col === "object" && col !== null
        ? { name: String(col.name || ""), dtype: String(col.dtype || "") }
        : { name: String(col), dtype: "" }
    ),
    [options]
  );
  const columnNames = useMemo(() => profileColumns.map((c) => c.name), [profileColumns]);

  const [newRenameFrom, setNewRenameFrom] = useState("");
  const [newRenameTo, setNewRenameTo] = useState("");

  const commit = useCallback(
    (nextParams) => {
      const cleaned = { ...nextParams };
      if (!normalizeColumns(cleaned.columns).length) delete cleaned.columns;
      if (!Object.keys(normalizeObject(cleaned.cast)).length) delete cleaned.cast;
      if (!Object.keys(normalizeObject(cleaned.renames)).length) delete cleaned.renames;
      if (cleaned.auto_clean_currency == null) delete cleaned.auto_clean_currency;
      if (cleaned.fiscal_year_column === "") delete cleaned.fiscal_year_column;
      onChange(Object.keys(cleaned).length > 0 ? cleaned : undefined);
    },
    [onChange]
  );

  const setField = useCallback(
    (fieldName, nextValue) => {
      const next = { ...params };
      if (nextValue === undefined || nextValue === null) {
        delete next[fieldName];
      } else {
        next[fieldName] = nextValue;
      }
      commit(next);
    },
    [params, commit]
  );

  // --- Column include/exclude ---
  const columns = normalizeColumns(params.columns);
  const filterActive = columns.length > 0;
  const includedSet = useMemo(() => new Set(columns), [columns]);

  const toggleFilterMode = useCallback(
    (enabled) => {
      if (enabled) {
        // Enable filter: include all current profile columns
        setField("columns", columnNames.length > 0 ? [...columnNames] : undefined);
      } else {
        setField("columns", undefined);
      }
    },
    [columnNames, setField]
  );

  const toggleColumn = useCallback(
    (columnName) => {
      if (!filterActive) return;
      const nextColumns = includedSet.has(columnName)
        ? columns.filter((col) => col !== columnName)
        : [...columns, columnName];
      setField("columns", nextColumns.length > 0 ? nextColumns : undefined);
    },
    [columns, includedSet, filterActive, setField]
  );

  // --- Cast ---
  const cast = normalizeObject(params.cast);

  const setCast = useCallback(
    (columnName, type) => {
      const next = { ...cast };
      if (!type) {
        delete next[columnName];
      } else {
        next[columnName] = type;
      }
      setField("cast", Object.keys(next).length > 0 ? next : undefined);
    },
    [cast, setField]
  );

  // --- Renames ---
  const renames = normalizeObject(params.renames);

  const addRename = useCallback(() => {
    const from = newRenameFrom.trim();
    const to = newRenameTo.trim();
    if (!from || !to) return;
    setField("renames", { ...renames, [from]: to });
    setNewRenameFrom("");
    setNewRenameTo("");
  }, [newRenameFrom, newRenameTo, setField, renames]);

  const updateRename = useCallback(
    (from, to) => {
      setField("renames", { ...renames, [from]: to });
    },
    [renames, setField]
  );

  const removeRename = useCallback(
    (from) => {
      const next = { ...renames };
      delete next[from];
      setField("renames", Object.keys(next).length > 0 ? next : undefined);
    },
    [renames, setField]
  );

  // --- Currency / Fiscal year ---
  const autoClean = params.auto_clean_currency;
  const autoCleanEnabled = autoClean === true || (isPlainObject(autoClean) && autoClean.enabled !== false);
  const multiplier = normalizeObject(autoClean).multiplier ?? 1;
  const fiscalYearColumn = params.fiscal_year_column;
  const fiscalYearDisabled = fiscalYearColumn === false;
  const fiscalYearColumnText = typeof fiscalYearColumn === "string" ? fiscalYearColumn : "";

  return html`
    <div class="data-params-widget">

      ${profileColumns.length > 0
        ? html`
          <div class="data-params-section">
            <h5 class="data-params-title">Column Configuration</h5>
            <p class="data-params-help">
              Review source columns. Optionally filter, cast types, or rename before binding.
            </p>

            <label class="data-params-checkbox" style=${{ marginBottom: "6px" }}>
              <input
                type="checkbox"
                checked=${filterActive}
                onChange=${(e) => toggleFilterMode(e.target.checked)}
              />
              <span>Include only selected columns</span>
            </label>

            <div class="column-config-grid">
              <div class="column-config-header">
                ${filterActive && html`<span class="column-config-hdr-cell column-config-hdr-include"></span>`}
                <span class="column-config-hdr-cell column-config-hdr-name">Column</span>
                <span class="column-config-hdr-cell column-config-hdr-dtype">Type</span>
                <span class="column-config-hdr-cell column-config-hdr-cast">Cast As</span>
              </div>
              ${profileColumns.map(
                (col) => html`
                  <div key=${col.name} class="column-config-row ${filterActive && !includedSet.has(col.name) ? "column-config-row--excluded" : ""}">
                    ${filterActive &&
                    html`
                      <span class="column-config-cell column-config-include">
                        <input
                          type="checkbox"
                          checked=${includedSet.has(col.name)}
                          onChange=${() => toggleColumn(col.name)}
                        />
                      </span>
                    `}
                    <span class="column-config-cell column-config-name">${col.name}</span>
                    <span class="column-config-cell column-config-dtype">${col.dtype}</span>
                    <span class="column-config-cell column-config-cast">
                      <select
                        class="column-config-select"
                        value=${cast[col.name] || ""}
                        onChange=${(e) => setCast(col.name, e.target.value)}
                      >
                        ${CAST_OPTIONS.map(
                          (t) => html`<option key=${t} value=${t}>${t || "\u2014"}</option>`
                        )}
                      </select>
                    </span>
                  </div>
                `
              )}
            </div>
          </div>
        `
        : html`
          <p class="column-config-empty">Run Test Source to see available columns.</p>
        `}

      <div class="data-params-section">
        <h5 class="data-params-title">Rename Columns</h5>
        ${Object.entries(renames).map(
          ([from, to]) => html`
            <div key=${from} class="data-params-row">
              <span class="data-params-key">${from}</span>
              <span class="data-params-arrow">\u2192</span>
              <input
                type="text"
                class="field-input"
                value=${String(to)}
                onInput=${(e) => updateRename(from, e.target.value)}
              />
              <button type="button" class="array-item-remove" onClick=${() => removeRename(from)}>\u00D7</button>
            </div>
          `
        )}

        <div class="data-params-inline">
          <input
            type="text"
            class="field-input"
            value=${newRenameFrom}
            placeholder="From"
            list="rename-columns"
            onInput=${(e) => setNewRenameFrom(e.target.value)}
          />
          <span class="data-params-arrow">\u2192</span>
          <input
            type="text"
            class="field-input"
            value=${newRenameTo}
            placeholder="To"
            onInput=${(e) => setNewRenameTo(e.target.value)}
          />
          <button
            type="button"
            class="btn btn-secondary"
            onClick=${addRename}
            disabled=${!newRenameFrom.trim() || !newRenameTo.trim()}
          >
            Add
          </button>
        </div>
        <datalist id="rename-columns">
          ${columnNames.map((col) => html`<option key=${col} value=${col} />`)}
        </datalist>
      </div>

      <div class="data-params-section">
        <label class="data-params-checkbox">
          <input
            type="checkbox"
            checked=${autoCleanEnabled}
            onChange=${(e) => {
              if (!e.target.checked) {
                setField("auto_clean_currency", undefined);
                return;
              }
              setField("auto_clean_currency", { enabled: true, multiplier });
            }}
          />
          <span>Auto-clean currency columns</span>
        </label>

        ${autoCleanEnabled &&
        html`
          <label class="data-params-field">
            <span>Multiplier</span>
            <input
              type="number"
              class="field-input"
              value=${multiplier}
              step="1"
              min="0"
              onInput=${(e) => {
                const next = e.target.value ? Number(e.target.value) : 1;
                setField("auto_clean_currency", { enabled: true, multiplier: next });
              }}
            />
          </label>
        `}
      </div>

      <div class="data-params-section">
        <label class="data-params-checkbox">
          <input
            type="checkbox"
            checked=${fiscalYearDisabled}
            onChange=${(e) => setField("fiscal_year_column", e.target.checked ? false : undefined)}
          />
          <span>Disable fiscal year column parsing</span>
        </label>

        ${!fiscalYearDisabled &&
        html`
          <label class="data-params-field">
            <span>Fiscal year column override</span>
            <input
              type="text"
              class="field-input"
              value=${fiscalYearColumnText}
              list="fiscal-year-columns"
              placeholder="Auto-detect when empty"
              onInput=${(e) =>
                setField("fiscal_year_column", e.target.value.trim() || undefined)}
            />
          </label>
        `}
        <datalist id="fiscal-year-columns">
          ${columnNames.map((col) => html`<option key=${col} value=${col} />`)}
        </datalist>
      </div>
    </div>
  `;
}
