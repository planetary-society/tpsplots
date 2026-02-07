/**
 * Metadata section: title, subtitle, source — always visible above RJSF form.
 */
import { useCallback, createElement } from "react";
import htm from "htm";

const html = htm.bind(createElement);

export function MetadataSection({ formData, onFormDataChange }) {
  const handleChange = useCallback((field, value) => {
    onFormDataChange({ ...formData, [field]: value });
  }, [formData, onFormDataChange]);

  return html`
    <div class="metadata-section">
      <div class="metadata-field">
        <label class="control-label" for="meta-title">Title *</label>
        <textarea
          id="meta-title"
          class="meta-input"
          value=${formData.title || ""}
          onInput=${(e) => handleChange("title", e.target.value)}
          placeholder="Chart title"
          rows="2"
        />
      </div>

      <div class="metadata-field">
        <label class="control-label" for="meta-subtitle">Subtitle</label>
        <textarea
          id="meta-subtitle"
          class="meta-input"
          value=${formData.subtitle || ""}
          onInput=${(e) => handleChange("subtitle", e.target.value)}
          placeholder="Subtitle (optional)"
          rows="2"
        />
      </div>

      <div class="metadata-row">
        <div class="metadata-field" style=${{ flex: 1 }}>
          <label class="control-label" for="meta-output">Output filename</label>
          <input
            id="meta-output"
            type="text"
            value=${formData.output || ""}
            onInput=${(e) => handleChange("output", e.target.value)}
            placeholder="output_name"
          />
        </div>

        <div class="metadata-field" style=${{ flex: 1 }}>
          <label class="control-label" for="meta-source">Source</label>
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
