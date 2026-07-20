/**
 * Metadata section: eyebrow, title, subtitle, note, source, output fields.
 */
import { useCallback } from "react";
import { html } from "../lib/html.js";
import { decodeEscapes, encodeEscapes } from "../lib/escapedText.js";

export function MetadataSection({ formData, onFormDataChange }) {
  const handleChange = useCallback((field, value) => {
    onFormDataChange({ ...formData, [field]: value });
  }, [formData, onFormDataChange]);

  return html`
    <div class="metadata-section">
      <div class="metadata-field" data-field="eyebrow">
        <label class="control-label" for="meta-eyebrow" title="YAML key: eyebrow">Eyebrow</label>
        <input
          id="meta-eyebrow"
          type="text"
          value=${encodeEscapes(formData.eyebrow || "")}
          onInput=${(e) => handleChange("eyebrow", decodeEscapes(e.target.value))}
          placeholder="Kicker line above the title (optional)"
          title=${'Type \\n for a line break'}
        />
      </div>

      <div class="metadata-field" data-field="title">
        <label class="control-label" for="meta-title" title="YAML key: title">Chart Title *</label>
        <textarea
          id="meta-title"
          class="meta-input"
          value=${formData.title || ""}
          onInput=${(e) => handleChange("title", e.target.value)}
          placeholder="Chart title"
          rows="2"
        />
      </div>

      <div class="metadata-field" data-field="subtitle">
        <label class="control-label" for="meta-subtitle" title="YAML key: subtitle">
          Chart Subtitle
        </label>
        <textarea
          id="meta-subtitle"
          class="meta-input"
          value=${formData.subtitle || ""}
          onInput=${(e) => handleChange("subtitle", e.target.value)}
          placeholder="Subtitle (optional)"
          rows="2"
        />
      </div>

      <div class="metadata-field" data-field="note">
        <label class="control-label" for="meta-note" title="YAML key: note">Note</label>
        <textarea
          id="meta-note"
          class="meta-input"
          value=${formData.note || ""}
          onInput=${(e) => handleChange("note", e.target.value)}
          placeholder="Footnote below the chart (optional)"
          rows="2"
        />
      </div>

      <div class="metadata-row">
        <div class="metadata-field" data-field="output" style=${{ flex: 1 }}>
          <label class="control-label" for="meta-output" title="YAML key: output">
            Output File Name
          </label>
          <input
            id="meta-output"
            type="text"
            value=${formData.output || ""}
            onInput=${(e) => handleChange("output", e.target.value)}
            placeholder="output_name"
          />
        </div>

        <div class="metadata-field" data-field="source" style=${{ flex: 1 }}>
          <label class="control-label" for="meta-source" title="YAML key: source">
            Source Attribution
          </label>
          <input
            id="meta-source"
            type="text"
            value=${formData.source || ""}
            onInput=${(e) => handleChange("source", e.target.value)}
            placeholder="Data source attribution"
          />
        </div>
      </div>
    </div>
  `;
}
