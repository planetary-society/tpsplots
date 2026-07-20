/**
 * String field: text input or enum dropdown.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { decodeEscapes, encodeEscapes } from "../../lib/escapedText.js";
import { TemplateChipInput } from "./TemplateChipInput.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

export function StringField({ name, schema, value, onChange, uiSchema, rawTextMode = false }) {
  const handleChange = useCallback(
    (e) => onChange(e.target.value || undefined),
    [onChange]
  );

  // Single-line inputs can't hold a real newline, so `\n` typed into one means
  // a line break (same as in hand-written YAML). Raw-text mode is left alone:
  // those values are literal strings the user is editing verbatim.
  const handleTextChange = useCallback(
    (e) => onChange(decodeEscapes(e.target.value) || undefined),
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
        value=${rawTextMode ? (value ?? "") : encodeEscapes(value ?? "")}
        onInput=${rawTextMode ? handleChange : handleTextChange}
        placeholder=${schema?.default ?? ""}
      />
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
