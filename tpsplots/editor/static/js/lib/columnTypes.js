/**
 * One reading of a profiled dataframe column's type.
 *
 * `profile_data` ships each column's pandas dtype as a bare string, so the
 * frontend has to interpret it. Both the binding suggestions (BindingStep) and
 * the series quick-add list (SeriesTable) rank columns by that reading — they
 * must agree, so the dtype vocabulary lives here rather than in each consumer.
 */

/** @param {{name?: string, dtype?: string}} col */
export function classifyColumn(col) {
  const name = String(col?.name || "");
  const dtype = String(col?.dtype || "").toLowerCase();
  const lower = name.toLowerCase();
  return {
    name,
    isDate: dtype.includes("date") || dtype.includes("time") || lower.includes("year"),
    isNumeric:
      dtype.includes("int") ||
      dtype.includes("float") ||
      dtype.includes("double") ||
      dtype.includes("number"),
  };
}

/** True when the column's dtype reads as numeric. */
export function isNumericColumn(col) {
  return classifyColumn(col).isNumeric;
}
