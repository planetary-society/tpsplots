/**
 * Bring a form field into view.
 *
 * Two callers need this: the StatusStrip chips (jump to the field an issue
 * points at) and SchemaForm (reveal a field the user just added from the
 * "add option" combobox). They differ only in emphasis — flash vs. focus — so
 * the DOM contract (`[data-field="<name>"]` inside the form panel, wrapped in
 * an optional `<details>` group) lives here once rather than in each caller.
 *
 * @param {string} fieldName - the field's `data-field` value
 * @param {Object} [options]
 * @param {ParentNode} [options.root] - subtree to search (defaults to the form panel)
 * @param {ScrollLogicalPosition} [options.block] - scrollIntoView alignment
 * @param {boolean} [options.focus] - move focus to the field's first control
 * @param {boolean} [options.flash] - restart the `field-flash` highlight animation
 * @returns {boolean} true when the field was found and revealed
 */
const FOCUSABLE = [
  "input:not([type='hidden']):not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "button:not([disabled])",
].join(", ");

export function revealField(fieldName, options = {}) {
  const { root, block = "center", focus = false, flash = false } = options;
  const scope = root || document.querySelector(".form-panel");
  if (!fieldName || !scope) return false;

  // dataset comparison rather than an attribute selector: field names come
  // from the schema and never need CSS escaping this way.
  const field = [...scope.querySelectorAll("[data-field]")].find(
    (element) => element.dataset.field === fieldName
  );
  if (!field) return false;

  // A field inside a collapsed advanced group cannot be scrolled to until the
  // group is open.
  const group = field.closest("details");
  if (group) group.open = true;

  field.scrollIntoView({ behavior: "smooth", block });

  if (flash) {
    field.classList.remove("field-flash");
    void field.offsetWidth; // restart the animation
    field.classList.add("field-flash");
  }
  if (focus) {
    field.querySelector(FOCUSABLE)?.focus({ preventScroll: true });
  }
  return true;
}
