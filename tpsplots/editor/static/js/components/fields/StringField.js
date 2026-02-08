/**
 * String field: text input or enum dropdown.
 */
import { useCallback, createElement } from "react";
import htm from "htm";
import { TemplateChipInput } from "./TemplateChipInput.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

const html = htm.bind(createElement);

export function StringField({ name, schema, value, onChange, uiSchema }) {
  const handleChange = useCallback(
    (e) => onChange(e.target.value || undefined),
    [onChange]
  );

  const enums = schema?.enum;
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);

  if (enums) {
    return html`
      <div class="field-row">
        <label class="field-label" for=${name} title=${labelTitle}>${label}</label>
        <select id=${name} class="field-input" value=${value ?? ""} onChange=${handleChange}>
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
        class="field-input"
        value=${value ?? ""}
        onInput=${handleChange}
        placeholder=${schema?.default ?? ""}
      />
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
