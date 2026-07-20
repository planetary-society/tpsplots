/**
 * Shared controlled-numeric-text machinery for text inputs that commit
 * parsed numbers (NumberField, ReferenceLineBuilder's numeric cells).
 *
 * Holds raw display text plus an `emittedRef` of the last committed number,
 * so a field can tell its own committed edits (which echo back through
 * `value`) apart from EXTERNAL value changes — YAML load, union clear,
 * chart-type remap, array rewrites — and re-seed the display only for the
 * latter, preserving in-progress text like "3.".
 *
 * Options:
 *   value        — the committed numeric value (or undefined).
 *   parse        — text -> number | undefined (undefined = not committable).
 *   onCommit     — called with the parsed number, or undefined when
 *                  `commitEmpty` and the box is emptied.
 *   commitEmpty  — when true (NumberField), clearing the box commits
 *                  undefined (deletes the field). When false
 *                  (ReferenceLineBuilder), empty/invalid text commits
 *                  nothing so serialized arrays never gain nulls.
 *   restoreOnBlur — when true, an empty/invalid box snaps back to the
 *                  committed value on blur instead of leaving orphaned text.
 */
import { useCallback, useRef, useState } from "react";

export function useNumericText({ value, parse, onCommit, commitEmpty = true, restoreOnBlur = false }) {
  const [raw, setRaw] = useState(value != null ? String(value) : "");
  const emittedRef = useRef(value);

  // Re-seed on external change: `value` matches neither the number we last
  // emitted nor the number currently typed. Setting state during render is
  // intentional (React re-renders immediately) and avoids the one-frame
  // stale flash a useEffect would cause.
  if (value !== emittedRef.current && value !== parse(raw)) {
    emittedRef.current = value;
    setRaw(value != null ? String(value) : "");
  }

  const handleInput = useCallback(
    (e) => {
      const text = e.target.value;
      setRaw(text);

      if (text === "") {
        if (commitEmpty) {
          emittedRef.current = undefined;
          onCommit(undefined);
        }
        return;
      }

      const num = parse(text);
      if (num !== undefined) {
        emittedRef.current = num;
        onCommit(num);
      }
    },
    [onCommit, parse, commitEmpty]
  );

  const handleBlur = useCallback(() => {
    if (restoreOnBlur && (raw === "" || parse(raw) === undefined)) {
      setRaw(value != null ? String(value) : "");
    }
  }, [restoreOnBlur, raw, parse, value]);

  return { raw, handleInput, handleBlur };
}
