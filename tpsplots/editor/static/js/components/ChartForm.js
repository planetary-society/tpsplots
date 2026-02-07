/**
 * RJSF form wrapper with custom ObjectFieldTemplate for grouped sections.
 */
import React, { useMemo, useCallback, createElement } from "react";
import htm from "htm";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";

import { ColorWidget } from "../widgets/ColorWidget.js";

const html = htm.bind(createElement);

// Fields managed by MetadataSection — hidden from RJSF
const METADATA_FIELDS = new Set(["title", "subtitle", "source", "output", "type"]);

/**
 * Custom ObjectFieldTemplate: groups fields into collapsible <details> sections
 * using ui:groups from the uiSchema.
 */
function GroupedObjectFieldTemplate(props) {
  const { properties, uiSchema, formData } = props;

  const groups = uiSchema?.["ui:groups"] || [];

  // Build lookup: fieldName → rendered element
  const fieldMap = {};
  for (const prop of properties) {
    fieldMap[prop.name] = prop.content;
  }

  return html`
    <div class="grouped-form">
      ${groups.map(group => {
        const visibleFields = group.fields.filter(
          f => !METADATA_FIELDS.has(f) && fieldMap[f]
        );
        if (visibleFields.length === 0) return null;

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
              ${visibleFields.map(f => html`<div key=${f} class="form-group">${fieldMap[f]}</div>`)}
            </div>
          </details>
        `;
      })}
      ${/* Hidden fields still rendered for form state */
        [...METADATA_FIELDS].map(f =>
          fieldMap[f]
            ? html`<div key=${f} style=${{ display: "none" }}>${fieldMap[f]}</div>`
            : null
        )
      }
    </div>
  `;
}

export function ChartForm({ schema, uiSchema, formData, colors, onFormDataChange }) {
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

  const widgets = useMemo(() => ({
    tpsColor: ColorWidget,
  }), []);

  const templates = useMemo(() => ({
    ObjectFieldTemplate: GroupedObjectFieldTemplate,
  }), []);

  const handleChange = useCallback((e) => {
    onFormDataChange(e.formData);
  }, [onFormDataChange]);

  if (!schema) return null;

  return html`
    <div class="chart-form">
      <${Form}
        schema=${schema}
        uiSchema=${enhancedUiSchema}
        formData=${formData}
        validator=${validator}
        onChange=${handleChange}
        templates=${templates}
        widgets=${widgets}
        liveValidate=${false}
        showErrorList=${false}
        omitExtraData=${false}
      >
        <${React.Fragment} />
      <//>
    </div>
  `;
}
