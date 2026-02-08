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
  if (typeof first === "number") return "number";
  return "string";
}

function parseItem(text, type) {
  if (type === "number") {
    const n = parseFloat(text);
    return isNaN(n) ? text : n;
  }
  return text;
}

export function ArrayField({ name, schema, value, onChange, uiSchema }) {
  const arr = Array.isArray(value) ? value : [];
  const itemType = inferItemType(arr);
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
    onChange([...arr, itemType === "number" ? 0 : ""]);
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
                <${TemplateChipInput}
                  inputMode=${itemType === "number" ? "numeric" : "text"}
                  class="array-item-input"
                  value=${item != null ? String(item) : ""}
                  onInput=${(e) => handleItemChange(idx, e.target.value)}
                />
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
