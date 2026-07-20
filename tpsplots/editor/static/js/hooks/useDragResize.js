/**
 * Shared pointer-drag resize machinery (form-panel width, YAML-pane height).
 *
 * Owns the mousemove/mouseup document-listener lifecycle; the caller owns the
 * size state and persistence. `axis: "x"` grows with rightward drag; `"y"`
 * grows with upward drag (bottom drawer).
 */
import { useCallback } from "react";

export function useDragResize({ axis, min, max, value, onChange, onStart, onEnd }) {
  return useCallback(
    (e) => {
      e.preventDefault();
      onStart?.();
      const startPos = axis === "x" ? e.clientX : e.clientY;
      const startValue = value;

      const onMove = (moveEvent) => {
        const pos = axis === "x" ? moveEvent.clientX : moveEvent.clientY;
        const delta = axis === "x" ? pos - startPos : startPos - pos;
        const upper = typeof max === "function" ? max() : max;
        onChange(Math.max(min, Math.min(upper, startValue + delta)));
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        onEnd?.();
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    },
    [axis, min, max, value, onChange, onStart, onEnd]
  );
}
