/**
 * Number/integer field with basic type validation.
 * Input machinery shared with ReferenceLineBuilder via lib/numericText.js.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { useNumericText } from "../../lib/numericText.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

/** Parse display text into a number for this field's schema type (or undefined). */
function parseNumber(text, schema) {
  if (text === "") return undefined;
  const num = schema?.type === "integer" ? parseInt(text, 10) : parseFloat(text);
  return isNaN(num) ? undefined : num;
}

export function NumberField({ name, schema, value, onChange, uiSchema }) {
  const parse = useCallback((text) => parseNumber(text, schema), [schema]);
  const { raw, handleInput } = useNumericText({
    value,
    parse,
    onCommit: onChange,
    commitEmpty: true,
  });

  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);

  return html`
    <div class="field-row">
      <label class="field-label" for=${name} title=${labelTitle}>${label}</label>
      <input
        id=${name}
        type="text"
        inputmode="numeric"
        class="field-input ${raw !== "" && isNaN(Number(raw)) ? "field-invalid" : ""}"
        value=${raw}
        onInput=${handleInput}
        placeholder=${schema?.default ?? ""}
      />
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
