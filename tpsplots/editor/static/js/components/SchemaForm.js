/**
 * Schema-driven form component — replaces RJSF.
 *
 * Reads JSON Schema properties to render appropriate field widgets,
 * handles anyOf (union types) natively via UnionField, and groups
 * fields into collapsible sections using ui:groups from the backend.
 */
import { useCallback, useMemo } from "react";
import { html } from "../lib/html.js";

import { FIELD_COMPONENTS } from "./fields/fieldComponents.js";
import { StringField } from "./fields/StringField.js";
import { UnionField } from "./fields/UnionField.js";
import { formatFieldLabel, yamlKeyTooltip } from "./fields/fieldLabelUtils.js";
import { resolveSchemaRef } from "./fields/schemaRefUtils.js";

const DEFAULT_HIDDEN_FIELDS = new Set(["title", "subtitle", "source", "output", "type"]);

/**
 * Select the right field component for a schema property.
 *
 * Returns [Component, effectiveSchema]:
 *   - For simple types: the matching component + the property schema
 *   - For anyOf: UnionField + the original schema (branches preserved)
 *   - For custom widgets (tpsColor): the provided widget
 */
function resolveFieldComponent(fieldName, propSchema, uiSchema, customWidgets) {
  // Custom widget override
  const widgetName = uiSchema?.[fieldName]?.["ui:widget"];
  if (widgetName && widgetName !== "hidden" && customWidgets?.[widgetName]) {
    return [customWidgets[widgetName], propSchema, "custom"];
  }

  // anyOf — use UnionField
  if (propSchema?.anyOf) {
    return [UnionField, propSchema, "union"];
  }

  // Simple type
  const type = propSchema?.type;
  const Component = FIELD_COMPONENTS[type];
  if (Component) {
    return [Component, propSchema, "simple"];
  }

  // Fallback: string
  return [StringField, { ...propSchema, type: "string" }, "fallback"];
}

export function SchemaForm({
  schema,
  uiSchema,
  formData,
  onChange,
  widgets,
  hiddenFields = DEFAULT_HIDDEN_FIELDS,
}) {
  const properties = schema?.properties || {};
  const groups = uiSchema?.["ui:groups"] || [];
  const order = uiSchema?.["ui:order"] || Object.keys(properties);
  const layoutRows = uiSchema?.["ui:layout"]?.rows || [];

  // Build a set of fields that are part of inline rows
  const rowFields = useMemo(() => {
    const s = new Set();
    for (const row of layoutRows) {
      for (const f of row) s.add(f);
    }
    return s;
  }, [layoutRows]);

  // Build a set of all fields assigned to any group
  const groupedFields = useMemo(() => {
    const s = new Set();
    for (const g of groups) {
      for (const f of g.fields) s.add(f);
    }
    return s;
  }, [groups]);

  // Per-field change handler: updates the single field in formData
  const handleFieldChange = useCallback(
    (fieldName, value) => {
      const next = { ...formData };
      if (value === undefined) {
        delete next[fieldName];
      } else {
        next[fieldName] = value;
      }
      onChange(next);
    },
    [formData, onChange]
  );

  // Render a single field
  const renderField = useCallback(
    (fieldName) => {
      const rawPropSchema = properties[fieldName];
      const propSchema = resolveSchemaRef(rawPropSchema, schema);
      if (!propSchema) return null;

      // Hidden fields
      if (uiSchema?.[fieldName]?.["ui:widget"] === "hidden") return null;

      const [FieldComponent, effectiveSchema, kind] = resolveFieldComponent(
        fieldName,
        propSchema,
        uiSchema,
        widgets
      );

      const fieldUiSchema = uiSchema?.[fieldName] || {};
      const value = formData?.[fieldName];
      const label = formatFieldLabel(fieldName, effectiveSchema);
      const labelTitle = yamlKeyTooltip(fieldName);

      // Custom widgets (like ColorWidget) use {value, onChange, options}
      if (kind === "custom") {
        const options = fieldUiSchema["ui:options"] || {};
        const help = fieldUiSchema["ui:help"];
        return html`
          <div class="field-row" key=${fieldName}>
            <label class="field-label" title=${labelTitle}>${label}</label>
            ${help && html`<span class="field-help">${help}</span>`}
            <${FieldComponent}
              value=${value}
              onChange=${(v) => handleFieldChange(fieldName, v)}
              options=${options}
              schema=${effectiveSchema}
            />
          </div>
        `;
      }

      return html`
        <${FieldComponent}
          key=${fieldName}
          name=${fieldName}
          schema=${effectiveSchema}
          value=${value}
          onChange=${(v) => handleFieldChange(fieldName, v)}
          uiSchema=${fieldUiSchema}
          rootSchema=${schema}
        />
      `;
    },
    [properties, uiSchema, formData, widgets, handleFieldChange, schema]
  );

  // Render an inline row of fields (e.g. xlim + ylim side by side)
  const renderRow = useCallback(
    (row) => {
      const fields = row.filter((f) => properties[f] && !hiddenFields.has(f));
      if (fields.length === 0) return null;
      return html`
        <div class="field-inline-row" key=${row.join("-")}>
          ${fields.map((f) => html`<div class="field-inline-col" key=${f}>${renderField(f)}</div>`)}
        </div>
      `;
    },
    [properties, renderField, hiddenFields]
  );

  // Fields not assigned to any group, respecting ui:order
  const ungroupedOrder = useMemo(() => {
    return order.filter(
      (f) => !groupedFields.has(f) && !hiddenFields.has(f) && properties[f]
    );
  }, [order, groupedFields, hiddenFields, properties]);

  return html`
    <div class="schema-form">
      ${groups.map((group) => {
        const visibleFields = group.fields.filter((f) => !hiddenFields.has(f) && properties[f]);
        if (visibleFields.length === 0) return null;

        // Split into row fields and standalone fields
        const standalone = visibleFields.filter((f) => !rowFields.has(f));
        const rowsInGroup = layoutRows.filter((row) =>
          row.some((f) => visibleFields.includes(f))
        );

        return html`
          <details
            key=${group.name}
            class="field-group"
            open=${group.defaultOpen || false}
          >
            <summary>
              <span class="group-arrow"></span>
              <span class="group-name">${group.name}</span>
              <span class="group-badge">${visibleFields.length}</span>
            </summary>
            <div class="group-fields">
              ${standalone.map((f) => html`<div key=${f} class="form-group">${renderField(f)}</div>`)}
              ${rowsInGroup.map((row) => renderRow(row))}
            </div>
          </details>
        `;
      })}
      ${ungroupedOrder
        .filter((f) => !rowFields.has(f))
        .map((f) => html`<div key=${f} class="form-group">${renderField(f)}</div>`)}
      ${layoutRows
        .filter((row) => row.some((f) => ungroupedOrder.includes(f)))
        .map((row) => renderRow(row))}
    </div>
  `;
}
