/**
 * Single status strip: the one place preflight state is shown.
 *
 * Replaces the old per-step ValidationSummary + preview-blocking
 * PreflightPanel. Each issue renders as a clickable chip that scrolls to and
 * flashes the offending field in the form panel. Priority (highest wins the
 * leading summary): validation errors > missing fields > all clear.
 */
import { useCallback, useMemo } from "react";
import { html } from "../lib/html.js";
import { fieldFromPath } from "../lib/preflightPaths.js";

function chipLabel(path, message) {
  const field = fieldFromPath(path);
  if (path?.startsWith("/data")) return "Data source";
  if (field) return field.replaceAll("_", " ");
  return message?.slice(0, 40) || "Issue";
}

export function scrollToField(fieldName) {
  const el = document.querySelector(`.form-panel [data-field="${fieldName}"]`);
  if (!el) return false;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.remove("field-flash");
  // Restart the flash animation.
  void el.offsetWidth;
  el.classList.add("field-flash");
  return true;
}

export function StatusStrip({ preflight }) {
  const issues = useMemo(() => {
    if (!preflight) return [];
    const fromErrors = (preflight.blocking_errors || []).map((e) => ({
      kind: "error",
      path: e.path,
      message: e.message,
    }));
    const fromMissing = (preflight.missing_paths || []).map((p) => ({
      kind: "missing",
      path: p,
      message: "Required",
    }));
    return [...fromErrors, ...fromMissing];
  }, [preflight]);

  const handleChipClick = useCallback((issue) => {
    const field = fieldFromPath(issue.path);
    if (field) scrollToField(field);
  }, []);

  if (!preflight) {
    return html`<div class="status-strip is-neutral">Checking…</div>`;
  }

  if (issues.length === 0) {
    return html`<div class="status-strip is-ok" title="Configuration is valid">✓ Ready</div>`;
  }

  const hasErrors = issues.some((i) => i.kind === "error");
  return html`
    <div class="status-strip ${hasErrors ? "is-error" : "is-warning"}">
      <span class="status-strip-summary">
        ${issues.length === 1 ? "1 issue" : `${issues.length} issues`}
      </span>
      ${issues.slice(0, 4).map(
        (issue, i) => html`
          <button
            key=${i}
            type="button"
            class="status-chip status-chip-${issue.kind}"
            title=${issue.message}
            onClick=${() => handleChipClick(issue)}
          >
            ${chipLabel(issue.path, issue.message)}
          </button>
        `
      )}
      ${issues.length > 4 && html`<span class="status-strip-more">+${issues.length - 4}</span>`}
    </div>
  `;
}
