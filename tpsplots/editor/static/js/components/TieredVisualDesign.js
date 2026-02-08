/**
 * 3-tier visual design wrapper for Step 3.
 *
 * Splits visual design fields into three progressive disclosure zones:
 *   1. Essential (always visible) — fields used in 60%+ of real configs
 *   2. Common (one-click expand) — fields used in 20-60% of configs
 *   3. Advanced (collapsed) — everything else
 *
 * Each zone delegates to ChartForm with an includeFields filter.
 */
import { useMemo } from "react";
import { html } from "../lib/html.js";

import { ChartForm } from "./ChartForm.js";
import { ReferenceLineBuilder } from "./ReferenceLineBuilder.js";

const EMPTY_SET = new Set();

export function TieredVisualDesign({
  schema,
  uiSchema,
  formData,
  colors,
  onFormDataChange,
  fieldTiers,
  compositeWidgets,
  seriesExcluded,
  visualFields,
}) {
  const essentialSet = useMemo(
    () => new Set(fieldTiers?.essential || []),
    [fieldTiers]
  );
  const commonSet = useMemo(
    () => new Set(fieldTiers?.common || []),
    [fieldTiers]
  );

  // Collect all fields consumed by composite widgets (rendered separately)
  const compositeFields = useMemo(() => {
    if (!compositeWidgets) return EMPTY_SET;
    const fields = new Set();
    for (const widget of Object.values(compositeWidgets)) {
      for (const f of widget.fields || []) fields.add(f);
      for (const f of widget.global_fields || []) fields.add(f);
    }
    return fields;
  }, [compositeWidgets]);

  // Fields already handled by the series editor in Step 2
  const excludedSet = useMemo(
    () => new Set(seriesExcluded || []),
    [seriesExcluded]
  );

  // Compute the advanced set: everything not essential, common,
  // composite-consumed, or series-excluded
  const advancedSet = useMemo(() => {
    const all = new Set(visualFields || Object.keys(schema?.properties || {}));
    const result = new Set();
    for (const f of all) {
      if (
        !essentialSet.has(f) &&
        !commonSet.has(f) &&
        !compositeFields.has(f) &&
        !excludedSet.has(f)
      ) {
        result.add(f);
      }
    }
    return result;
  }, [schema, visualFields, essentialSet, commonSet, compositeFields, excludedSet]);

  // Filter out excluded/composite fields from essential and common sets
  const filteredEssential = useMemo(() => {
    const result = new Set();
    for (const f of essentialSet) {
      if (!excludedSet.has(f) && !compositeFields.has(f)) result.add(f);
    }
    return result;
  }, [essentialSet, excludedSet, compositeFields]);

  const filteredCommon = useMemo(() => {
    const result = new Set();
    for (const f of commonSet) {
      if (!excludedSet.has(f) && !compositeFields.has(f)) result.add(f);
    }
    return result;
  }, [commonSet, excludedSet, compositeFields]);

  const hasRefLines = compositeWidgets?.reference_lines != null;

  return html`
    <div class="tiered-design">
      ${filteredEssential.size > 0 &&
      html`
        <${ChartForm}
          schema=${schema}
          uiSchema=${uiSchema}
          formData=${formData}
          colors=${colors}
          onFormDataChange=${onFormDataChange}
          includeFields=${filteredEssential}
        />
      `}

      ${hasRefLines &&
      html`
        <${ReferenceLineBuilder}
          formData=${formData}
          onFormDataChange=${onFormDataChange}
          colors=${colors}
          config=${compositeWidgets.reference_lines}
          schema=${schema}
          uiSchema=${uiSchema}
        />
      `}

      ${filteredCommon.size > 0 &&
      html`
        <details class="tier-section tier-common">
          <summary class="tier-summary">
            <span class="tier-arrow">\u25B8</span>
            More Options
            <span class="tier-badge">${filteredCommon.size}</span>
          </summary>
          <div class="tier-content">
            <${ChartForm}
              schema=${schema}
              uiSchema=${uiSchema}
              formData=${formData}
              colors=${colors}
              onFormDataChange=${onFormDataChange}
              includeFields=${filteredCommon}
            />
          </div>
        </details>
      `}

      ${advancedSet.size > 0 &&
      html`
        <details class="tier-section tier-advanced">
          <summary class="tier-summary">
            <span class="tier-arrow">\u25B8</span>
            Advanced
            <span class="tier-badge">${advancedSet.size}</span>
          </summary>
          <div class="tier-content">
            <${ChartForm}
              schema=${schema}
              uiSchema=${uiSchema}
              formData=${formData}
              colors=${colors}
              onFormDataChange=${onFormDataChange}
              includeFields=${advancedSet}
            />
          </div>
        </details>
      `}
    </div>
  `;
}
