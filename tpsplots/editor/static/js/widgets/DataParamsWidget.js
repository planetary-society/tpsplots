/**
 * Purpose-built editor for DataSourceConfig.params.
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

export function DataParamsWidget({ value, onChange, options }) {
  const params = normalizeObject(value);
  const availableColumns = useMemo(
    () => (options?.availableColumns || []).map((col) => String(col)),
    [options]
  );

  const [newColumn, setNewColumn] = useState("");
  const [newCastKey, setNewCastKey] = useState("");
  const [newCastType, setNewCastType] = useState("str");
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

  const columns = normalizeColumns(params.columns);
  const selectedColumns = new Set(columns);

  const toggleColumn = useCallback(
    (columnName) => {
      const exists = selectedColumns.has(columnName);
      const nextColumns = exists
        ? columns.filter((col) => col !== columnName)
        : [...columns, columnName];
      setField("columns", nextColumns.length > 0 ? nextColumns : undefined);
    },
    [columns, selectedColumns, setField]
  );

  const addColumn = useCallback(() => {
    const name = newColumn.trim();
    if (!name || selectedColumns.has(name)) return;
    setField("columns", [...columns, name]);
    setNewColumn("");
  }, [newColumn, selectedColumns, setField, columns]);

  const cast = normalizeObject(params.cast);
  const renames = normalizeObject(params.renames);
  const autoClean = params.auto_clean_currency;
  const autoCleanEnabled = autoClean === true || (isPlainObject(autoClean) && autoClean.enabled !== false);
  const multiplier = normalizeObject(autoClean).multiplier ?? 1;
  const fiscalYearColumn = params.fiscal_year_column;
  const fiscalYearDisabled = fiscalYearColumn === false;
  const fiscalYearColumnText = typeof fiscalYearColumn === "string" ? fiscalYearColumn : "";

  const addCast = useCallback(() => {
    const key = newCastKey.trim();
    if (!key) return;
    setField("cast", { ...cast, [key]: newCastType });
    setNewCastKey("");
  }, [newCastKey, newCastType, setField, cast]);

  const updateCast = useCallback(
    (key, type) => {
      setField("cast", { ...cast, [key]: type });
    },
    [cast, setField]
  );

  const removeCast = useCallback(
    (key) => {
      const next = { ...cast };
      delete next[key];
      setField("cast", Object.keys(next).length > 0 ? next : undefined);
    },
    [cast, setField]
  );

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

  return html`
    <div class="data-params-widget">
      <div class="data-params-section">
        <h5 class="data-params-title">Columns</h5>
        <p class="data-params-help">Limit source data to selected columns.</p>

        <div class="binding-suggestions">
          ${availableColumns.map(
            (col) => html`
              <button
                key=${col}
                type="button"
                class=${`binding-suggestion ${
                  selectedColumns.has(col) ? "binding-suggestion--selected" : ""
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
          <button type="button" class="btn btn-secondary" onClick=${addColumn} disabled=${!newColumn.trim()}>
            Add
          </button>
        </div>
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

      <details class="data-params-advanced" open=${Object.keys(cast).length > 0 || Object.keys(renames).length > 0 || fiscalYearColumn !== undefined}>
        <summary>Advanced parameters</summary>

        <div class="data-params-section">
          <h5 class="data-params-title">Cast</h5>
          ${Object.entries(cast).map(
            ([key, type]) => html`
              <div key=${key} class="data-params-row">
                <span class="data-params-key">${key}</span>
                <select
                  class="field-input"
                  value=${String(type)}
                  onChange=${(e) => updateCast(key, e.target.value)}
                >
                  ${["str", "int", "float", "datetime", "bool"].map(
                    (castType) => html`<option key=${castType} value=${castType}>${castType}</option>`
                  )}
                </select>
                <button type="button" class="array-item-remove" onClick=${() => removeCast(key)}>×</button>
              </div>
            `
          )}

          <div class="data-params-inline">
            <input
              type="text"
              class="field-input"
              value=${newCastKey}
              placeholder="Column name"
              onInput=${(e) => setNewCastKey(e.target.value)}
            />
            <select
              class="field-input"
              value=${newCastType}
              onChange=${(e) => setNewCastType(e.target.value)}
            >
              ${["str", "int", "float", "datetime", "bool"].map(
                (castType) => html`<option key=${castType} value=${castType}>${castType}</option>`
              )}
            </select>
            <button type="button" class="btn btn-secondary" onClick=${addCast} disabled=${!newCastKey.trim()}>
              Add
            </button>
          </div>
        </div>

        <div class="data-params-section">
          <h5 class="data-params-title">Renames</h5>
          ${Object.entries(renames).map(
            ([from, to]) => html`
              <div key=${from} class="data-params-row">
                <span class="data-params-key">${from}</span>
                <input
                  type="text"
                  class="field-input"
                  value=${String(to)}
                  onInput=${(e) => updateRename(from, e.target.value)}
                />
                <button type="button" class="array-item-remove" onClick=${() => removeRename(from)}>×</button>
              </div>
            `
          )}

          <div class="data-params-inline">
            <input
              type="text"
              class="field-input"
              value=${newRenameFrom}
              placeholder="From"
              onInput=${(e) => setNewRenameFrom(e.target.value)}
            />
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
        </div>
      </details>

      <datalist id="fiscal-year-columns">
        ${availableColumns.map((col) => html`<option key=${col} value=${col} />`)}
      </datalist>
    </div>
  `;
}
