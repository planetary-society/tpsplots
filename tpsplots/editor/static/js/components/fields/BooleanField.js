/**
 * Boolean field: checkbox.
 */
import { useCallback } from "react";
import { html } from "../../lib/html.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";

export function BooleanField({ name, value, onChange, schema, uiSchema }) {
  const handleChange = useCallback(
    (e) => onChange(e.target.checked),
    [onChange]
  );

  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name);
  const labelTitle = yamlKeyTooltip(name);

  // When the value is unset, reflect the model default so a field that
  // defaults to `true` (e.g. treemap show_labels/show_percentages) renders
  // checked instead of misreporting the behavior as off.
  //
  // Note: SchemaForm passes the property schema here (includes `default`), so
  // the simple-field path is fully covered. In the UnionField (anyOf) path the
  // component receives a single branch schema, which carries no `default` — the
  // default lives on the property level and UnionField does not forward it, so
  // union-typed booleans fall back to the unchecked-when-unset behavior.
  const checked = value == null ? schema?.default === true : value === true;

  return html`
    <div class="field-row field-row-checkbox">
      <label class="field-label" for=${name} title=${labelTitle}>
        <input
          id=${name}
          type="checkbox"
          checked=${checked}
          onChange=${handleChange}
        />
        ${" " + label}
      </label>
      ${help && html`<span class="field-help">${help}</span>`}
    </div>
  `;
}
