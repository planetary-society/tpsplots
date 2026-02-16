/**
 * Boolean field: checkbox.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

export function BooleanField({ name, value, onChange, uiSchema }) {
  const handleChange = useCallback(
    (e) => onChange(e.target.checked),
    [onChange]
  );

  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name);
  const labelTitle = yamlKeyTooltip(name);

  return html`
    <div class="field-row field-row-checkbox">
      <label class="field-label" for=${name} title=${labelTitle}>
        <input
          id=${name}
          type="checkbox"
          checked=${value === true}
          onChange=${handleChange}
        />
        ${" " + label}
      </label>
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
