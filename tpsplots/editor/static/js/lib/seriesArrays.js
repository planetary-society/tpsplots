/**
 * Pure helpers for the per-series parallel arrays used by line/scatter charts.
 *
 * Line and scatter charts store per-series styling as parallel ("correlated")
 * arrays on formData: `color`, `labels`, `linestyle`, `linewidth`, `marker`,
 * `markersize`, `alpha`. Each of these arrays is indexed positionally against
 * the chart's series.
 *
 * THE CONCATENATED-INDEX CONTRACT
 * -------------------------------
 * A chart can carry two axes of series: the left axis (`y`) and the right axis
 * (`y_right`). The series list the UI renders is the CONCATENATION
 * `[...leftSeries, ...rightSeries]` (see SeriesTable). The correlated arrays
 * index across that SAME concatenation, so:
 *
 *   - concatenated index of left-axis series i  === i
 *   - concatenated index of right-axis series i === leftCount + i
 *
 * where `leftCount` is the number of left-axis (`y`) series. Every helper here
 * that touches a specific series takes an `axisField` ("y" or "y_right") plus a
 * per-axis index, and translates it to the concatenated index using the axis
 * offset. Callers must pass the same hint object the backend emits as
 * `series_correlated_fields`:
 *
 *   { trigger_field, secondary_trigger_field, correlated: [...fieldNames] }
 *
 * This module is intentionally free of React imports so it can be unit-tested
 * as plain functions.
 */

/** String-typed correlated fields whose Pydantic model accepts `list[str | None]`. */
const STRING_SERIES_FIELDS = new Set(["color", "labels", "linestyle", "marker"]);

/**
 * Backfill defaults for numeric correlated fields. These are `list[float]` on
 * the Pydantic model and reject interior nulls, so gaps must be filled.
 */
const NUMERIC_SERIES_DEFAULTS = { linewidth: 1.5, markersize: 6, alpha: 1.0 };

/**
 * True when `fieldName` is a numeric correlated field (`list[float]`, no nulls).
 * @param {string} fieldName
 * @returns {boolean}
 */
export function isNumericSeriesField(fieldName) {
  return Object.prototype.hasOwnProperty.call(NUMERIC_SERIES_DEFAULTS, fieldName);
}

/**
 * The default value used to backfill interior gaps of a numeric field, or
 * `undefined` for string fields (which accept `null` gaps unchanged).
 * @param {string} fieldName
 * @returns {number|undefined}
 */
export function numericSeriesDefault(fieldName) {
  return isNumericSeriesField(fieldName) ? NUMERIC_SERIES_DEFAULTS[fieldName] : undefined;
}

/** True when `fieldName` is a string correlated field (`list[str | None]`). */
export function isStringSeriesField(fieldName) {
  return STRING_SERIES_FIELDS.has(fieldName);
}

/**
 * Read the effective value of a correlated field for one series row.
 *
 * A correlated field may be stored three ways on formData:
 *   - an array   → the value at that series index (may be a `null`/`undefined` gap)
 *   - a scalar   → applies to EVERY series, so it is returned for every index
 *   - null/undefined → the field is unset, so `undefined` is returned
 *
 * Unifying scalar handling here lets a YAML scalar (`markersize: 12`,
 * `color: "Neptune Blue"`, `linestyle: "--"`) display on every series row.
 *
 * @param {*} value - formData[fieldName] (array, scalar, or nullish)
 * @param {number} index - concatenated series index
 * @returns {*} the value for that row, or `undefined` when unset
 */
export function seriesValueAt(value, index) {
  if (Array.isArray(value)) return value[index];
  if (value === null || value === undefined) return undefined;
  return value;
}

/**
 * Compute the next value of a correlated field after editing ONE series row.
 *
 * Handles the three storage shapes described in {@link seriesValueAt}:
 *   - Existing array → cloned and edited in place.
 *   - Existing scalar → seeded across ALL `seriesCount` rows first (the scalar
 *     applied to every series), then the single edit is applied, so untouched
 *     rows keep the former scalar instead of being dropped.
 *   - Nothing → a fresh sparse array.
 *
 * String fields (color/labels/linestyle/marker) keep interior `null` gaps —
 * the Pydantic model accepts `list[str | None]`, so styling only the 3rd of 3
 * series yields the valid `[null, null, "X"]`. Numeric fields
 * (linewidth/markersize/alpha) are `list[float]` and reject nulls, so pass
 * their `numericDefault` (see {@link numericSeriesDefault}) to backfill gaps.
 *
 * No brand-cycle / visual placeholder is ever written — only real values the
 * caller supplies or an existing scalar are stored.
 *
 * @param {*} existing - current formData[fieldName]
 * @param {number} seriesIndex - concatenated index of the edited row
 * @param {number} seriesCount - combined left+right series count
 * @param {*} newValue - edited value; nullish or "" clears that row
 * @param {number|undefined} numericDefault - backfill for numeric fields; omit for string fields
 * @returns {Array|undefined} the next array, or `undefined` to remove the field entirely
 */
export function writeSeriesValue(existing, seriesIndex, seriesCount, newValue, numericDefault) {
  let arr;
  if (Array.isArray(existing)) {
    arr = [...existing];
  } else if (existing !== undefined && existing !== null) {
    // Scalar applies to every series — seed all rows so untouched rows keep it.
    arr = new Array(seriesCount).fill(existing);
  } else {
    arr = [];
  }

  // Grow with explicit null gaps up to the edited index. Interior nulls are
  // valid for string fields and are backfilled below for numeric fields.
  while (arr.length <= seriesIndex) arr.push(null);

  const cleared = newValue === undefined || newValue === null || newValue === "";
  arr[seriesIndex] = cleared ? null : newValue;

  // Trim trailing gaps (matches both null and undefined).
  while (arr.length > 0 && arr[arr.length - 1] == null) arr.pop();

  // Fully cleared → signal caller to drop the field.
  if (arr.length === 0) return undefined;

  if (numericDefault !== undefined) {
    for (let j = 0; j < arr.length; j += 1) {
      if (arr[j] == null) arr[j] = numericDefault;
    }
  }

  return arr;
}

/** Number of series carried by an axis field value (array, scalar, or unset). */
function axisSeriesCount(value) {
  if (Array.isArray(value)) return value.length;
  return value !== undefined && value !== null && value !== "" ? 1 : 0;
}

/**
 * Concatenated-index offset for a given axis field. Left-axis (`y`) series map
 * directly (offset 0); right-axis (`y_right`) series sit after every left-axis
 * series, so their offset is the left-axis series count.
 *
 * @param {Object} formData
 * @param {Object} correlatedFields - hint object with trigger_field / secondary_trigger_field
 * @param {string} axisField - the axis being operated on ("y" or "y_right")
 * @returns {number}
 */
function concatOffset(formData, correlatedFields, axisField) {
  const secondary = correlatedFields?.secondary_trigger_field;
  if (!secondary || axisField !== secondary) return 0;
  return axisSeriesCount(formData?.[correlatedFields?.trigger_field]);
}

/**
 * Atomically swap two series positions across EVERY correlated array present on
 * formData, so per-series styling follows its series when the binding order
 * changes.
 *
 * Indices are per-axis and translated to concatenated indices via the axis
 * offset (see the concatenated-index contract at the top of this module).
 * Fields are left untouched when they are:
 *   - absent from formData, or
 *   - stored as a scalar (a scalar applies to all series — reordering is a no-op), or
 *   - an array SHORTER than the touched (larger) concatenated index — there is
 *     nothing to move at that position.
 *
 * Returns a new formData object (never mutates); returns the input unchanged
 * when nothing was permuted.
 *
 * @param {Object} formData
 * @param {Object} correlatedFields - `series_correlated_fields` hint object
 * @param {string} axisField - axis being reordered ("y" or "y_right")
 * @param {number} fromIndex - per-axis source index
 * @param {number} toIndex - per-axis destination index
 * @returns {Object} next formData
 */
export function permuteCorrelated(formData, correlatedFields, axisField, fromIndex, toIndex) {
  const fields = correlatedFields?.correlated;
  if (!formData || !Array.isArray(fields) || fields.length === 0) return formData;

  const offset = concatOffset(formData, correlatedFields, axisField);
  const from = offset + fromIndex;
  const to = offset + toIndex;
  if (from === to) return formData;

  const touched = Math.max(from, to);
  let changed = false;
  const next = { ...formData };
  for (const field of fields) {
    const value = formData[field];
    if (!Array.isArray(value)) continue; // scalar or absent → untouched
    if (value.length <= touched) continue; // shorter than touched index → untouched
    const arr = [...value];
    [arr[from], arr[to]] = [arr[to], arr[from]];
    next[field] = arr;
    changed = true;
  }
  return changed ? next : formData;
}

/**
 * Atomically remove one series position from EVERY correlated array present on
 * formData, so removing a series does not silently re-style the survivors.
 *
 * The per-axis `index` is translated to a concatenated index via the axis
 * offset (see the concatenated-index contract at the top of this module).
 * Fields are left untouched when they are absent, stored as a scalar, or an
 * array SHORTER than the concatenated index (nothing to remove there).
 *
 * Returns a new formData object (never mutates); returns the input unchanged
 * when nothing was spliced.
 *
 * @param {Object} formData
 * @param {Object} correlatedFields - `series_correlated_fields` hint object
 * @param {string} axisField - axis the removed series belongs to ("y" or "y_right")
 * @param {number} index - per-axis index of the removed series
 * @returns {Object} next formData
 */
export function spliceCorrelated(formData, correlatedFields, axisField, index) {
  const fields = correlatedFields?.correlated;
  if (!formData || !Array.isArray(fields) || fields.length === 0) return formData;

  const at = concatOffset(formData, correlatedFields, axisField) + index;
  let changed = false;
  const next = { ...formData };
  for (const field of fields) {
    const value = formData[field];
    if (!Array.isArray(value)) continue; // scalar or absent → untouched
    if (value.length <= at) continue; // shorter than touched index → untouched
    const arr = [...value];
    arr.splice(at, 1);
    next[field] = arr;
    changed = true;
  }
  return changed ? next : formData;
}

/**
 * Normalize an axis binding value (formData.y / formData.y_right) into a
 * clean string array: scalar string → [scalar], array → strings only,
 * unset/empty → [].
 */
export function normalizeBindings(value) {
  if (Array.isArray(value)) return value.filter((item) => typeof item === "string");
  if (typeof value === "string" && value.trim() !== "") return [value];
  return [];
}

/**
 * Collapse a binding array back to its minimal formData shape: [] → undefined
 * (field removed), [one] → the scalar, [many] → the array. Mirrors the
 * scalar/`list[str]` duality of the config models.
 */
export function bindingFieldValue(bindings) {
  const cleaned = bindings
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
  if (cleaned.length === 0) return undefined;
  if (cleaned.length === 1) return cleaned[0];
  return cleaned;
}
