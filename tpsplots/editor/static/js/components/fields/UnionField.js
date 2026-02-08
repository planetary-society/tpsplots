/**
 * Union field: handles anyOf schemas by detecting the current value's type
 * and rendering the matching field component.
 *
 * When value is null/undefined, shows a type selector dropdown.
 */
import { useCallback, createElement } from "react";
import htm from "htm";

import { StringField } from "./StringField.js";
import { NumberField } from "./NumberField.js";
import { BooleanField } from "./BooleanField.js";
import { ObjectField } from "./ObjectField.js";
import { ArrayField } from "./ArrayField.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";
import { resolveSchemaRef } from "./schemaRefUtils.js";

const html = htm.bind(createElement);

/** Extract available non-null types from anyOf branches. */
function getAnyOfTypes(schema, rootSchema) {
  const branches = schema?.anyOf || [];
  const types = [];
  for (const rawBranch of branches) {
    const branch = resolveSchemaRef(rawBranch, rootSchema);
    const t = branch?.type;
    if (t && t !== "null") types.push(t);
  }
  return types.length > 0 ? types : ["string"];
}

/** Detect the JS type of a value and map to JSON Schema type. */
function detectValueType(val) {
  if (val == null) return null;
  if (typeof val === "boolean") return "boolean";
  if (typeof val === "number") return Number.isInteger(val) ? "integer" : "number";
  if (Array.isArray(val)) return "array";
  if (typeof val === "object") return "object";
  return "string";
}

/** Find the matching anyOf branch schema for a given type. */
function branchForType(schema, type, rootSchema) {
  const branches = schema?.anyOf || [];
  for (const rawBranch of branches) {
    const branch = resolveSchemaRef(rawBranch, rootSchema);
    if (branch?.type === type) return branch;
    // "number" also matches "integer"
    if (type === "integer" && branch?.type === "number") return branch;
  }
  return { type: type || "string" };
}

/** Map JSON Schema type to a human-readable label. */
const TYPE_LABELS = {
  boolean: "Checkbox",
  integer: "Number",
  number: "Number",
  string: "Text",
  object: "Dictionary",
  array: "List",
};

/** Default value for a type when switching. */
const TYPE_DEFAULTS = {
  boolean: false,
  integer: 0,
  number: 0,
  string: "",
  object: {},
  array: [],
};

const FIELD_MAP = {
  string: StringField,
  integer: NumberField,
  number: NumberField,
  boolean: BooleanField,
  object: ObjectField,
  array: ArrayField,
};

export function UnionField({ name, schema, value, onChange, uiSchema, rootSchema }) {
  const availableTypes = getAnyOfTypes(schema, rootSchema);
  const currentType = detectValueType(value);
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);

  const handleTypeSwitch = useCallback(
    (e) => {
      const newType = e.target.value;
      if (newType === "") {
        onChange(undefined);
      } else {
        onChange(TYPE_DEFAULTS[newType] ?? "");
      }
    },
    [onChange]
  );

  const handleClear = useCallback(() => onChange(undefined), [onChange]);

  // No value set — show type selector
  if (currentType === null) {
    return html`
      <div class="field-row">
        <label class="field-label" title=${labelTitle}>${label}</label>
        ${help && html`<span class="field-help">${help}</span>`}
        <select class="field-input union-type-select" onChange=${handleTypeSwitch} value="">
          <option value="">— not set —</option>
          ${availableTypes.map(
            (t) => html`<option key=${t} value=${t}>${TYPE_LABELS[t] || t}</option>`
          )}
        </select>
      </div>
    `;
  }

  // Value exists — render the matching field with a type indicator + clear button
  const FieldComponent = FIELD_MAP[currentType] || StringField;
  const branchSchema = branchForType(schema, currentType, rootSchema);

  return html`
    <div class="union-field-wrapper">
      <div class="union-type-bar">
        <select
          class="union-type-switch"
          value=${currentType}
          onChange=${handleTypeSwitch}
          title="Switch type"
        >
          ${availableTypes.map(
            (t) => html`<option key=${t} value=${t}>${TYPE_LABELS[t] || t}</option>`
          )}
        </select>
        <button
          type="button"
          class="union-clear-btn"
          onClick=${handleClear}
          title="Clear value"
        >
          \u00d7
        </button>
      </div>
      <${FieldComponent}
        name=${name}
        schema=${branchSchema}
        value=${value}
        onChange=${onChange}
        uiSchema=${uiSchema}
        rootSchema=${rootSchema}
      />
    </div>
  `;
}
