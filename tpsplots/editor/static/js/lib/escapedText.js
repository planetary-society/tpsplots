/**
 * Backslash-escape translation for single-line text inputs.
 *
 * Hand-written YAML spells a line break inside chart text as `\n`
 * ("Annual\nExpenditure"), and matplotlib renders the real newline. A
 * single-line <input> can't hold a real newline, so users type the escape
 * sequence and it used to reach the chart literally.
 *
 * These helpers keep the *stored* value canonical (a real newline, same as
 * YAML) while the *displayed* value stays escaped and editable on one line:
 *
 *   input shows `Annual\nExpenditure`
 *     --decodeEscapes-->  config/YAML holds a real newline
 *     --encodeEscapes-->  input shows `Annual\nExpenditure` again
 *
 * Backslashes are handled pairwise so a literal backslash survives the round
 * trip: `\\n` displays and stores as backslash + "n", only a lone `\n` is a
 * line break.
 */

/** Escaped display text → stored value (`\n` becomes a real newline). */
export function decodeEscapes(text) {
  if (typeof text !== "string" || !text.includes("\\")) return text;
  return text.replace(/\\+n/g, (match) => {
    const slashes = match.length - 1;
    const literal = "\\".repeat(Math.floor(slashes / 2));
    return slashes % 2 === 1 ? `${literal}\n` : `${literal}n`;
  });
}

/** Stored value → escaped display text (newlines become `\n`). */
export function encodeEscapes(text) {
  if (typeof text !== "string") return text;
  return text.replace(/\\/g, "\\\\").replace(/\n/g, "\\n");
}
