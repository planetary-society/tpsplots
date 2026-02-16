/**
 * Array field: editable list with add/remove items.
 * Infers item type from existing values.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { TemplateChipInput } from "./TemplateChipInput.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

function inferItemType(arr) {
  if (!arr || arr.length === 0) return "string";
  const first = arr[0];
  if (typeof first === "boolean") return "boolean";
  if (Number.isInteger(first)) return "integer";
  if (typeof first === "number") return "number";
  return "string";
}

function schemaItemType(schema) {
  const itemType = schema?.items?.type;
  if (typeof itemType === "string") return itemType;
  if (Array.isArray(itemType) && itemType.length > 0 && typeof itemType[0] === "string") {
    return itemType[0];
  }
  return null;
}

function resolveItemType(schema, arr) {
  const fromSchema = schemaItemType(schema);
  return fromSchema || inferItemType(arr);
}

function parseItem(text, type) {
  if (type === "number" || type === "integer") {
    const n = parseFloat(text);
    if (isNaN(n)) return text;
    if (type === "integer") return Math.trunc(n);
    return n;
  }
  if (type === "boolean") {
    if (text === true || text === false) return text;
    const normalized = String(text).trim().toLowerCase();
    if (normalized === "true") return true;
    if (normalized === "false") return false;
    return text;
  }
  return text;
}

export function ArrayField({ name, schema, value, onChange, uiSchema }) {
  const arr = Array.isArray(value) ? value : [];
  const itemType = resolveItemType(schema, arr);
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);

  const handleItemChange = useCallback(
    (idx, text) => {
      const next = [...arr];
      next[idx] = parseItem(text, itemType);
      onChange(next);
    },
    [arr, itemType, onChange]
  );

  const handleRemove = useCallback(
    (idx) => {
      const next = arr.filter((_, i) => i !== idx);
      onChange(next.length > 0 ? next : undefined);
    },
    [arr, onChange]
  );

  const handleAdd = useCallback(() => {
    if (itemType === "boolean") {
      onChange([...arr, false]);
      return;
    }
    if (itemType === "number" || itemType === "integer") {
      onChange([...arr, 0]);
      return;
    }
    onChange([...arr, ""]);
  }, [arr, itemType, onChange]);

  return html`
    <div class="field-row">
      <label class="field-label" title=${labelTitle}>${label}</label>
      ${help && html`<span class="field-help">${help}</span>`}
      <div class="array-items">
        ${arr.map(
          (item, idx) => html`
            <div key=${idx} class="array-item">
              <div class="array-item-main">
                ${itemType === "boolean"
                  ? html`
                      <label class="array-item-boolean">
                        <input
                          type="checkbox"
                          checked=${item === true}
                          onChange=${(e) => handleItemChange(idx, e.target.checked)}
                        />
                        <span>${item === true ? "true" : "false"}</span>
                      </label>
                    `
                  : html`
                      <${TemplateChipInput}
                        inputMode=${itemType === "number" || itemType === "integer" ? "numeric" : "text"}
                        class="array-item-input"
                        value=${item != null ? String(item) : ""}
                        onInput=${(e) => handleItemChange(idx, e.target.value)}
                      />
                    `}
              </div>
              <button
                type="button"
                class="array-item-remove"
                onClick=${() => handleRemove(idx)}
                title="Remove"
              >
                \u00d7
              </button>
            </div>
          `
        )}
        <button type="button" class="array-add-btn" onClick=${handleAdd}>
          + Add item
        </button>
      </div>
    </div>
  `;
}
