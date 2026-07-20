/**
 * Shared listbox keyboard navigation for filtered dropdown lists
 * (AddOptionCombobox, the Open-file menu): ArrowUp/Down clamp-move the
 * active row, Enter commits it, Escape closes.
 *
 * The caller owns the filtered list and renders rows; this hook owns the
 * active index and the keydown protocol. Call `setActiveIndex` from row
 * onMouseEnter to keep hover and keyboard selection in sync, and reset the
 * index when the filter changes.
 */
import { useCallback, useState } from "react";

export function useListboxNav({ length, onCommit, onClose }) {
  const [activeIndex, setActiveIndex] = useState(0);

  const onKeyDown = useCallback(
    (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        onCommit?.(activeIndex);
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose?.();
      }
    },
    [length, activeIndex, onCommit, onClose]
  );

  return { activeIndex, setActiveIndex, onKeyDown };
}
