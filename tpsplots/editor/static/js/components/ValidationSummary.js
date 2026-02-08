/**
 * Compact preflight summary with "next action" guidance.
 */
import { createElement } from "react";
import htm from "htm";

const html = htm.bind(createElement);

function humanizePath(path) {
  if (!path) return "General";
  return path.replace(/^\//, "").replaceAll("/", " \u2192 ");
}

export function ValidationSummary({ preflight }) {
  if (!preflight) {
    return html`<div class="validation-summary is-neutral">Checking configuration\u2026</div>`;
  }

  if (preflight.ready_for_preview) {
    return html`
      <div class="validation-summary is-success">
        <strong>Ready:</strong> Data source and required bindings are valid.
      </div>
    `;
  }

  const firstMissing = preflight.missing_paths?.[0];
  const firstBlocking = preflight.blocking_errors?.[0];

  if (firstMissing) {
    return html`
      <div class="validation-summary is-warning">
        <strong>Next required action:</strong> fill <code>${humanizePath(firstMissing)}</code>.
      </div>
    `;
  }

  if (firstBlocking) {
    return html`
      <div class="validation-summary is-error">
        <strong>Blocking issue:</strong> ${humanizePath(firstBlocking.path)} \u2014 ${firstBlocking.message}
      </div>
    `;
  }

  return html`
    <div class="validation-summary is-warning">
      <strong>Needs review:</strong> complete required data and binding fields.
    </div>
  `;
}

