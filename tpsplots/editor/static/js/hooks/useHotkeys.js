/**
 * Core editor hotkeys.
 */
import { useEffect, useRef } from "react";

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
  const ref = useRef(handlers);
  ref.current = handlers;

  useEffect(() => {
    const onKeyDown = (e) => {
      const mod = e.metaKey || e.ctrlKey;
      const editable = isEditableTarget(e.target);

      if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        ref.current.onSave?.();
        return;
      }

      if (mod && e.key.toLowerCase() === "o") {
        e.preventDefault();
        ref.current.onOpen?.();
        return;
      }

      if (mod && e.key === "Enter") {
        e.preventDefault();
        ref.current.onForceRender?.();
        return;
      }

      if (mod && e.shiftKey && e.key.toLowerCase() === "m") {
        e.preventDefault();
        ref.current.onToggleDevice?.();
        return;
      }

      if (!editable && e.altKey && ["1", "2", "3", "4"].includes(e.key)) {
        e.preventDefault();
        ref.current.onSetStep?.(Number(e.key));
        return;
      }

      if (!editable && !mod && !e.altKey && !e.shiftKey) {
        const key = e.key.toLowerCase();
        if (key === "d") {
          ref.current.onSetDevice?.("desktop");
          return;
        }
        if (key === "m") {
          ref.current.onSetDevice?.("mobile");
          return;
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);
}
