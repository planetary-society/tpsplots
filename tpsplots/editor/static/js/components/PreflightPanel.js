/**
 * Preview-side checklist for preflight blockers.
 */
import { html } from "../lib/html.js";

function humanize(path) {
  return path?.replace(/^\//, "").replaceAll("/", " \u2192 ") || "General";
}

export function PreflightPanel({ preflight }) {
  if (!preflight || preflight.ready_for_preview) return null;

  return html`
    <div class="preflight-panel">
      <h4>Fix before preview</h4>

      ${(preflight.missing_paths || []).length > 0 &&
      html`
        <div class="preflight-group">
          <strong>Missing required fields</strong>
          <ul>
            ${preflight.missing_paths.map((path) => html`<li key=${path}><code>${humanize(path)}</code></li>`)}
          </ul>
        </div>
      `}

      ${(preflight.blocking_errors || []).length > 0 &&
      html`
        <div class="preflight-group">
          <strong>Blocking issues</strong>
          <ul>
            ${preflight.blocking_errors.map(
              (err, idx) =>
                html`<li key=${idx}><code>${humanize(err.path)}</code>: ${err.message}</li>`
            )}
          </ul>
        </div>
      `}
    </div>
  `;
}

