/**
 * Object / key-value field for dict params (e.g. legend: {loc: "upper right"}).
 *
 * Supports add/remove keys, auto-detects value type per entry.
 */
import { useState, useEffect, useCallback, createElement } from "react";
import htm from "htm";
import { TemplateChipInput } from "./TemplateChipInput.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

const html = htm.bind(createElement);

function detectType(val) {
  if (val === true || val === false) return "boolean";
  if (typeof val === "number") return "number";
  if (Array.isArray(val)) return "array";
  if (val && typeof val === "object") return "object";
  return "string";
}

function parseValue(text, type) {
  if (type === "number") {
    const n = parseFloat(text);
    return isNaN(n) ? text : n;
  }
  if (type === "boolean") return text === "true";
  return text;
}

function parseComplex(text, type) {
  try {
    const parsed = JSON.parse(text);
    if (type === "array") return Array.isArray(parsed) ? parsed : null;
    if (type === "object") return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
    return null;
  } catch {
    return null;
  }
}

function canonicalComplexText(val, type) {
  if (type === "array" && !Array.isArray(val)) return "[]";
  if (type === "object" && (!val || typeof val !== "object" || Array.isArray(val))) return "{}";
  try {
    return JSON.stringify(val, null, 2);
  } catch {
    return type === "array" ? "[]" : "{}";
  }
}

function ValueInput({ entryKey, val, onValueChange }) {
  const type = detectType(val);
  const [complexText, setComplexText] = useState(() => canonicalComplexText(val, type));
  const [complexInvalid, setComplexInvalid] = useState(false);

  useEffect(() => {
    if (type === "array" || type === "object") {
      setComplexText(canonicalComplexText(val, type));
      setComplexInvalid(false);
    }
  }, [val, type]);

  if (type === "boolean") {
    return html`
      <input
        type="checkbox"
        checked=${val === true}
        onChange=${(e) => onValueChange(entryKey, e.target.checked)}
        class="obj-value-input obj-value-checkbox"
      />
    `;
  }

  if (type === "array" || type === "object") {
    return html`
      <div class="obj-value-wrap obj-complex-wrap">
        <textarea
          class=${`obj-value-input obj-complex-input ${complexInvalid ? "invalid" : ""}`}
          value=${complexText}
          rows="3"
          onInput=${(e) => {
            const text = e.target.value;
            setComplexText(text);
            const parsed = parseComplex(text, type);
            if (parsed == null) {
              setComplexInvalid(true);
              return;
            }
            setComplexInvalid(false);
            onValueChange(entryKey, parsed);
          }}
          onBlur=${() => {
            if (!complexInvalid) return;
            setComplexText(canonicalComplexText(val, type));
            setComplexInvalid(false);
          }}
        />
      </div>
    `;
  }

  return html`
    <div class="obj-value-wrap">
      <${TemplateChipInput}
        type="text"
        inputMode=${type === "number" ? "numeric" : "text"}
        class="obj-value-input"
        value=${val != null ? String(val) : ""}
        onInput=${(e) => onValueChange(entryKey, parseValue(e.target.value, type))}
      />
    </div>
  `;
}

export function ObjectField({ name, schema, value, onChange, uiSchema }) {
  const [newKey, setNewKey] = useState("");
  const obj = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const entries = Object.entries(obj);
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);

  const handleValueChange = useCallback(
    (key, val) => {
      onChange({ ...obj, [key]: val });
    },
    [obj, onChange]
  );

  const handleRemove = useCallback(
    (key) => {
      const next = { ...obj };
      delete next[key];
      // If empty, signal removal
      onChange(Object.keys(next).length > 0 ? next : undefined);
    },
    [obj, onChange]
  );

  const handleAdd = useCallback(() => {
    const key = newKey.trim();
    if (!key || key in obj) return;
    onChange({ ...obj, [key]: "" });
    setNewKey("");
  }, [newKey, obj, onChange]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleAdd();
      }
    },
    [handleAdd]
  );

  return html`
    <div class="field-row">
      <label class="field-label" title=${labelTitle}>${label}</label>
      ${help && html`<span class="field-help">${help}</span>`}
      <div class="obj-entries">
        ${entries.map(
          ([k, v]) => html`
            <div key=${k} class="obj-entry">
              <span class="obj-key">${k}</span>
              <${ValueInput}
                entryKey=${k}
                val=${v}
                onValueChange=${handleValueChange}
              />
              <button
                type="button"
                class="obj-remove"
                onClick=${() => handleRemove(k)}
                title="Remove"
              >
                \u00d7
              </button>
            </div>
          `
        )}
        <div class="obj-add-row">
          <input
            type="text"
            class="obj-key-input"
            value=${newKey}
            onInput=${(e) => setNewKey(e.target.value)}
            onKeyDown=${handleKeyDown}
            placeholder="new key"
          />
          <button
            type="button"
            class="obj-add-btn"
            onClick=${handleAdd}
            disabled=${!newKey.trim()}
          >
            + Add
          </button>
        </div>
      </div>
    </div>
  `;
}
