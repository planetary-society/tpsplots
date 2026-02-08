/**
 * Union field: handles anyOf schemas by detecting the current value's type
 * and rendering the matching field component.
 *
 * When value is null/undefined, shows a type selector dropdown.
 */
import { useCallback, useEffect, useRef } from "react";
import { html } from "../../lib/html.js";

import { FIELD_COMPONENTS } from "./fieldComponents.js";
import { StringField } from "./StringField.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fieldLabelUtils.js";
import { resolveSchemaRef } from "./schemaRefUtils.js";

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
  string: "Raw Text",
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

function stringifyForText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    if (value.length === 0) return "";
    const primitiveOnly = value.every(
      (item) =>
        item == null ||
        typeof item === "string" ||
        typeof item === "number" ||
        typeof item === "boolean"
    );
    if (primitiveOnly) {
      return value
        .map((item) => (item == null ? "" : String(item)))
        .filter((item) => item.trim() !== "")
        .join(",");
    }
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  return String(value);
}

function parseStringAsArray(value) {
  const trimmed = typeof value === "string" ? value.trim() : "";
  if (!trimmed) return [];

  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      // Fall through to comma parsing.
    }
  }

  const parts = trimmed.split(",").map((item) => item.trim()).filter(Boolean);
  return parts.length > 1 ? parts : [trimmed];
}

function parseStringAsObject(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value;
  }
  if (typeof value !== "string" || value.trim() === "") {
    return TYPE_DEFAULTS.object;
  }
  try {
    const parsed = JSON.parse(value);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
  } catch {
    // Keep default.
  }
  return TYPE_DEFAULTS.object;
}

function convertValueForType(value, targetType) {
  if (targetType === "") return undefined;

  if (targetType === "array") {
    if (Array.isArray(value)) return value;
    if (value == null) return [];
    if (typeof value === "string") return parseStringAsArray(value);
    if (typeof value === "number" || typeof value === "boolean") return [value];
    if (typeof value === "object") {
      try {
        return [JSON.stringify(value)];
      } catch {
        return TYPE_DEFAULTS.array;
      }
    }
    return TYPE_DEFAULTS.array;
  }

  if (targetType === "string") {
    return stringifyForText(value);
  }

  if (targetType === "number" || targetType === "integer") {
    if (typeof value === "number") return targetType === "integer" ? Math.trunc(value) : value;
    if (Array.isArray(value) && value.length > 0) {
      const parsed = Number(value[0]);
      if (!Number.isNaN(parsed)) {
        return targetType === "integer" ? Math.trunc(parsed) : parsed;
      }
    }
    if (typeof value === "string" && value.trim() !== "") {
      const parsed = Number(value);
      if (!Number.isNaN(parsed)) {
        return targetType === "integer" ? Math.trunc(parsed) : parsed;
      }
    }
    return TYPE_DEFAULTS[targetType];
  }

  if (targetType === "boolean") {
    if (typeof value === "boolean") return value;
    if (typeof value === "string") {
      const lower = value.trim().toLowerCase();
      if (lower === "true") return true;
      if (lower === "false") return false;
    }
    if (Array.isArray(value) && value.length > 0) {
      const first = String(value[0]).trim().toLowerCase();
      if (first === "true") return true;
      if (first === "false") return false;
    }
    return TYPE_DEFAULTS.boolean;
  }

  if (targetType === "object") {
    return parseStringAsObject(value);
  }

  return TYPE_DEFAULTS[targetType] ?? "";
}

export function UnionField({ name, schema, value, onChange, uiSchema, rootSchema }) {
  const availableTypes = getAnyOfTypes(schema, rootSchema);
  const currentType = detectValueType(value);
  const help = uiSchema?.["ui:help"];
  const label = formatFieldLabel(name, schema);
  const labelTitle = yamlKeyTooltip(name);
  const valueCacheRef = useRef({});

  useEffect(() => {
    if (currentType !== null) {
      valueCacheRef.current[currentType] = value;
    }
  }, [currentType, value]);

  const handleTypeSwitch = useCallback(
    (e) => {
      const newType = e.target.value;
      if (currentType !== null) {
        valueCacheRef.current[currentType] = value;
      }

      const cached = valueCacheRef.current[newType];
      const converted = cached !== undefined ? cached : convertValueForType(value, newType);
      onChange(converted);
    },
    [onChange, value, currentType]
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
  const FieldComponent = FIELD_COMPONENTS[currentType] || StringField;
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
        rawTextMode=${currentType === "string"}
      />
    </div>
  `;
}
