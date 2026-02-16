/**
 * String field: text input or enum dropdown.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { TemplateChipInput } from "./TemplateChipInput.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

export function StringField({ name, schema, value, onChange, uiSchema, rawTextMode = false }) {
  const handleChange = useCallback(
    (e) => onChange(e.target.value || undefined),
    [onChange]
  );

  const enums = schema?.enum;
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);
  const inputClass = rawTextMode ? "field-input field-input-mono" : "field-input";

  if (enums) {
    return html`
      <div class="field-row">
        <label class="field-label" for=${name} title=${labelTitle}>${label}</label>
        <select id=${name} class=${inputClass} value=${value ?? ""} onChange=${handleChange}>
          <option value="">— none —</option>
          ${enums.map(v => html`<option key=${v} value=${v}>${v}</option>`)}
        </select>
        ${help && html`<span class="field-help">${help}</span>`}
      </div>
    `;
  }

  return html`
    <div class="field-row">
      <label class="field-label" for=${name} title=${labelTitle}>${label}</label>
      <${TemplateChipInput}
        id=${name}
        class=${inputClass}
        value=${value ?? ""}
        onInput=${handleChange}
        placeholder=${schema?.default ?? ""}
      />
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
