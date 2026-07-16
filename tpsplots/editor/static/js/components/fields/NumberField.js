/**
 * Number/integer field with basic type validation.
 */
import { useCallback, useRef, useState } from "react";
import { html } from "../../lib/html.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

/** Parse display text into a number for this field's schema type (or undefined). */
function parseNumber(text, schema) {
  if (text === "") return undefined;
  const num = schema?.type === "integer" ? parseInt(text, 10) : parseFloat(text);
  return isNaN(num) ? undefined : num;
}

export function NumberField({ name, schema, value, onChange, uiSchema }) {
  const [raw, setRaw] = useState(value != null ? String(value) : "");
  // Last value this field emitted via onChange. Lets us tell our own edits
  // (which echo back through `value`) apart from external value changes — YAML
  // load, union branch clear, chart-type remap in app.js, SeriesEditor array
  // writes — so we re-sync the display for those without clobbering typing.
  const emittedRef = useRef(value);

  // Re-seed the raw text when `value` changed externally: it matches neither
  // the number we last emitted nor the number currently typed. Comparing the
  // parsed raw preserves in-progress text like "3." while our own edits
  // round-trip. Setting state during render is intentional (React re-renders
  // immediately) and avoids the one-frame stale flash a useEffect would cause.
  if (value !== emittedRef.current && value !== parseNumber(raw, schema)) {
    emittedRef.current = value;
    setRaw(value != null ? String(value) : "");
  }

  const handleInput = useCallback(
    (e) => {
      const text = e.target.value;
      setRaw(text);

      if (text === "") {
        emittedRef.current = undefined;
        onChange(undefined);
        return;
      }

      const num = parseNumber(text, schema);
      if (num !== undefined) {
        emittedRef.current = num;
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
