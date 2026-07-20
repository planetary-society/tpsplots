/**
 * Shared parsing for backend preflight paths ("/data/source", "/chart/xlim/0").
 * One home for the path grammar so the StatusStrip chips and the section
 * badges can never drift apart.
 */

/** Chart field name from a preflight path, or "source" for data paths. */
export function fieldFromPath(path) {
  if (!path) return null;
  const parts = String(path).replace(/^\//, "").split("/");
  if (parts[0] === "chart" && parts.length > 1) return parts[1];
  if (parts[0] === "data") return "source";
  return null;
}

/**
 * Editor section ("data" | "chart" | "text") for a preflight path.
 * `textFields` is the annotation field set from editor_hints.step_field_map.
 */
export function sectionForPath(path, textFields) {
  if (!path) return "chart";
  if (String(path).startsWith("/data")) return "data";
  const field = fieldFromPath(path);
  return field && textFields.has(field) ? "text" : "chart";
}
