/**
 * Visual badge for template references like {{Column Name}}.
 */
import { html } from "../../lib/html.js";
import { parseTemplateReferences, stripTemplateBraces } from "./templateRefUtils.js";

export function TemplateRefChip({ value }) {
  const refs = parseTemplateReferences(value);
  if (refs.length === 0) return null;
  const chipLabel = stripTemplateBraces;
  return html`
    <span class="template-ref-chip-list" title="Template reference">
      ${refs.map(
        (ref, idx) =>
          html`<span key=${`${ref}-${idx}`} class="template-ref-chip">${chipLabel(ref)}</span>`
      )}
    </span>
  `;
}
