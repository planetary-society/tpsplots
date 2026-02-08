/**
 * Chart form wrapper: delegates to SchemaForm with TPS color options injected.
 */
import { useMemo, useCallback, createElement } from "react";
import htm from "htm";

import { SchemaForm } from "./SchemaForm.js";
import { ColorWidget } from "../widgets/ColorWidget.js";

const html = htm.bind(createElement);

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

  const widgets = useMemo(
    () => ({ tpsColor: ColorWidget }),
    []
  );

  const handleChange = useCallback(
    (data) => onFormDataChange(data),
    [onFormDataChange]
  );

  if (!schema) return null;

  return html`
    <div class="chart-form">
      <${SchemaForm}
        schema=${schema}
        uiSchema=${enhancedUiSchema}
        formData=${formData}
        onChange=${handleChange}
        widgets=${widgets}
      />
    </div>
  `;
}
