/**
 * Chart form wrapper: delegates to SchemaForm with TPS color options injected.
 */
import { useMemo, useCallback, createElement } from "react";
import htm from "htm";

import { SchemaForm } from "./SchemaForm.js";
import { ColorWidget } from "../widgets/ColorWidget.js";

const html = htm.bind(createElement);

const DEFAULT_HIDDEN_FIELDS = new Set(["title", "subtitle", "source", "output", "type"]);

function filterSchemaAndUi(schema, uiSchema, includeFields, excludeFields) {
  if (!schema) return { schema: null, uiSchema: uiSchema || {} };

  const include = includeFields ? new Set(includeFields) : null;
  const exclude = excludeFields ? new Set(excludeFields) : new Set();
  const allFields = Object.keys(schema.properties || {});
  const allowed = allFields.filter((f) => (!include || include.has(f)) && !exclude.has(f));

  const filteredSchema = {
    ...schema,
    properties: Object.fromEntries(
      Object.entries(schema.properties || {}).filter(([k]) => allowed.includes(k))
    ),
  };
  if (Array.isArray(schema.required)) {
    filteredSchema.required = schema.required.filter((f) => allowed.includes(f));
  }

  const filteredUi = { ...(uiSchema || {}) };
  for (const key of Object.keys(filteredUi)) {
    if (!key.startsWith("ui:") && !allowed.includes(key)) {
      delete filteredUi[key];
    }
  }
  if (Array.isArray(filteredUi["ui:order"])) {
    filteredUi["ui:order"] = filteredUi["ui:order"].filter((f) => allowed.includes(f));
  }
  if (Array.isArray(filteredUi["ui:groups"])) {
    filteredUi["ui:groups"] = filteredUi["ui:groups"]
      .map((group) => ({ ...group, fields: group.fields.filter((f) => allowed.includes(f)) }))
      .filter((group) => group.fields.length > 0);
  }
  if (filteredUi["ui:layout"]?.rows) {
    filteredUi["ui:layout"] = {
      ...filteredUi["ui:layout"],
      rows: filteredUi["ui:layout"].rows
        .map((row) => row.filter((f) => allowed.includes(f)))
        .filter((row) => row.length > 0),
    };
  }

  return { schema: filteredSchema, uiSchema: filteredUi };
}

export function ChartForm({
  schema,
  uiSchema,
  formData,
  colors,
  onFormDataChange,
  includeFields,
  excludeFields,
  hiddenFields = DEFAULT_HIDDEN_FIELDS,
}) {
  // Merge color options into uiSchema for color widgets
  const enhancedUiSchema = useMemo(() => {
    if (!uiSchema) return {};
    const enhanced = { ...uiSchema };

    // Pass TPS colors to all tpsColor widgets via ui:options
    for (const [field, fieldUi] of Object.entries(enhanced)) {
      if (fieldUi?.["ui:widget"] === "tpsColor") {
        enhanced[field] = {
          ...fieldUi,
          "ui:options": {
            ...fieldUi["ui:options"],
            tpsColors: colors?.tps_colors || {},
            semanticColors: colors?.colors || {},
          },
        };
      }
    }

    return enhanced;
  }, [uiSchema, colors]);

  const widgets = useMemo(() => ({ tpsColor: ColorWidget }), []);

  const filtered = useMemo(
    () => filterSchemaAndUi(schema, enhancedUiSchema, includeFields, excludeFields),
    [schema, enhancedUiSchema, includeFields, excludeFields]
  );

  const handleChange = useCallback(
    (data) => onFormDataChange(data),
    [onFormDataChange]
  );

  if (!filtered.schema) return null;

  return html`
    <div class="chart-form">
      <${SchemaForm}
        schema=${filtered.schema}
        uiSchema=${filtered.uiSchema}
        formData=${formData}
        onChange=${handleChange}
        widgets=${widgets}
        hiddenFields=${hiddenFields}
      />
    </div>
  `;
}
