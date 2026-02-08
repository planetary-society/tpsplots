/**
 * Number/integer field with basic type validation.
 */
import { useCallback, useState, createElement } from "react";
import htm from "htm";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

const html = htm.bind(createElement);

export function NumberField({ name, schema, value, onChange, uiSchema }) {
  const [raw, setRaw] = useState(value != null ? String(value) : "");

  const handleInput = useCallback(
    (e) => {
      const text = e.target.value;
      setRaw(text);

      if (text === "") {
        onChange(undefined);
        return;
      }

      const num = schema?.type === "integer" ? parseInt(text, 10) : parseFloat(text);
      if (!isNaN(num)) {
        onChange(num);
      }
    },
    [onChange, schema]
  );

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
