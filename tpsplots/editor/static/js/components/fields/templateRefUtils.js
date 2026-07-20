/**
 * Utilities for parsing {{...}} template reference text values.
 */

const TEMPLATE_REF_LIST_RE = /^\s*\{\{[^{}]+\}\}\s*(,\s*\{\{[^{}]+\}\}\s*)*$/;
const TEMPLATE_REF_TOKEN_RE = /\{\{[^{}]+\}\}/g;

export function parseTemplateReferences(value) {
  if (typeof value !== "string") return [];
  const trimmed = value.trim();
  if (!TEMPLATE_REF_LIST_RE.test(trimmed)) return [];
  const refs = trimmed.match(TEMPLATE_REF_TOKEN_RE);
  return refs ? refs : [];
}

export function isTemplateReference(value) {
  return parseTemplateReferences(value).length > 0;
}

/** "{{Column Name}}" -> "Column Name" (non-refs pass through unchanged). */
export function stripTemplateBraces(ref) {
  if (typeof ref !== "string") return String(ref ?? "");
  return ref.replace(/^\{\{\s*/, "").replace(/\s*\}\}$/, "");
}
