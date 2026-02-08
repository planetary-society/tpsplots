/**
 * Core editor hotkeys.
 */
import { useEffect } from "react";

function isEditableTarget(target) {
  if (!target) return false;
  const tag = target.tagName?.toLowerCase();
  return (
    tag === "input" ||
    tag === "textarea" ||
    tag === "select" ||
    target.isContentEditable
  );
}

export function useHotkeys(handlers) {
  useEffect(() => {
    const onKeyDown = (e) => {
      const mod = e.metaKey || e.ctrlKey;
      const editable = isEditableTarget(e.target);

      if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        handlers.onSave?.();
        return;
      }

      if (mod && e.key.toLowerCase() === "o") {
        e.preventDefault();
        handlers.onOpen?.();
        return;
      }

      if (mod && e.key === "Enter") {
        e.preventDefault();
        handlers.onForceRender?.();
        return;
      }

      if (mod && e.shiftKey && e.key.toLowerCase() === "m") {
        e.preventDefault();
        handlers.onToggleDevice?.();
        return;
      }

      if (!editable && e.altKey && ["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        handlers.onSetStep?.(Number(e.key));
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handlers]);
}

