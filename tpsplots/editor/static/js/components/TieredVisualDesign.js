/**
 * Tiered visual design wrapper for the styling step.
 *
 * Progressive disclosure zones:
 *   1. Essential (always visible) — fields used in 60%+ of real configs
 *   2. Common (one-click expand) — fields used in 20-60% of configs
 *   3. Everything else — zero pixels until added via the "Add option…"
 *      combobox (or already carrying a value, which keeps it visible so
 *      loaded configs never look lossy)
 *
 * Excluded fields (annotations, figsize, matplotlib_config) that carry
 * values render as read-only "YAML-only" chips pointing at the YAML pane.
 */
import { useMemo, useState } from "react";
import { html } from "../lib/html.js";

import { AddOptionCombobox } from "./AddOptionCombobox.js";
import { ChartForm } from "./ChartForm.js";
import { ReferenceLineBuilder } from "./ReferenceLineBuilder.js";
import { formatFieldLabel } from "./fields/fieldLabelUtils.js";

const EMPTY_SET = new Set();
const EMPTY_LIST = [];

/** Fields in `source` that appear in none of the `excluded` sets. */
function difference(source, ...excluded) {
  const result = new Set();
  for (const field of source) {
    if (!excluded.some((set) => set.has(field))) result.add(field);
  }
  return result;
}

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
  excludedFields = EMPTY_LIST,
  onOpenYaml,
}) {
  // Options the user explicitly added this session (renders their empty field).
  const [addedFields, setAddedFields] = useState(EMPTY_SET);
  const [revealField, setRevealField] = useState(null);
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
    return difference(all, essentialSet, commonSet, compositeFields, excludedSet);
  }, [schema, visualFields, essentialSet, commonSet, compositeFields, excludedSet]);

  // Filter out excluded/composite fields from essential and common sets
  const filteredEssential = useMemo(
    () => difference(essentialSet, excludedSet, compositeFields),
    [essentialSet, excludedSet, compositeFields]
  );

  const filteredCommon = useMemo(
    () => difference(commonSet, excludedSet, compositeFields),
    [commonSet, excludedSet, compositeFields]
  );

  const hasRefLines = compositeWidgets?.reference_lines != null;

  // Split the long tail: fields with values (or explicitly added) render as
  // normal inputs; the rest live behind the Add option… combobox.
  const visibleAdvanced = useMemo(() => {
    const result = new Set();
    for (const f of advancedSet) {
      if (formData?.[f] !== undefined || addedFields.has(f)) result.add(f);
    }
    return result;
  }, [advancedSet, formData, addedFields]);

  const addableOptions = useMemo(() => {
    const result = [];
    for (const f of advancedSet) {
      if (visibleAdvanced.has(f)) continue;
      const propSchema = schema?.properties?.[f];
      result.push({
        name: f,
        label: formatFieldLabel(f, propSchema),
        help: uiSchema?.[f]?.["ui:help"] || propSchema?.description || "",
      });
    }
    return result.sort((a, b) => a.label.localeCompare(b.label));
  }, [advancedSet, visibleAdvanced, schema, uiSchema]);

  // Excluded fields carrying values: visible as YAML-only chips so a loaded
  // config never looks lossy, but edited in the file (via the YAML pane).
  const yamlOnlyFields = useMemo(
    () => excludedFields.filter((f) => formData?.[f] !== undefined),
    [excludedFields, formData]
  );

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

      ${visibleAdvanced.size > 0 &&
      html`
        <div class="tier-section tier-added">
          <${ChartForm}
            schema=${schema}
            uiSchema=${uiSchema}
            formData=${formData}
            colors=${colors}
            onFormDataChange=${onFormDataChange}
            includeFields=${visibleAdvanced}
            revealField=${revealField}
          />
        </div>
      `}

      <${AddOptionCombobox}
        options=${addableOptions}
        onAdd=${(name) => {
          setAddedFields((prev) => new Set([...prev, name]));
          setRevealField(name);
        }}
      />

      ${yamlOnlyFields.length > 0 &&
      html`
        <div class="yaml-only-chips">
          ${yamlOnlyFields.map(
            (f) => html`
              <button
                key=${f}
                type="button"
                class="yaml-only-chip"
                title="Set in this chart's YAML \u2014 view in the YAML pane, edit in the file"
                onClick=${onOpenYaml}
              >
                ${formatFieldLabel(f)} <span class="yaml-only-tag">YAML</span>
              </button>
            `
          )}
        </div>
      `}
    </div>
  `;
}
