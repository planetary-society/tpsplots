/**
 * Mini inline color picker: shows the current swatch + dropdown of TPS colors.
 * Uses position:fixed so the dropdown escapes overflow:hidden ancestors.
 *
 * Shared between SeriesEditor and ReferenceLineBuilder.
 */
import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { html } from "../lib/html.js";

export function MiniColorPicker({ value, onChange, tpsColors }) {
  const [open, setOpen] = useState(false);
  const [dropStyle, setDropStyle] = useState(null);
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const entries = useMemo(() => Object.entries(tpsColors || {}), [tpsColors]);
  const resolvedHex = tpsColors?.[value] || value || "transparent";

  const handleSelect = useCallback(
    (name) => {
      onChange(name);
      setOpen(false);
    },
    [onChange]
  );

  // Calculate fixed position when opening
  const handleToggle = useCallback(() => {
    setOpen((prev) => {
      if (!prev && triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const dropHeight = 210; // max-height + margin
        const placeAbove = spaceBelow < dropHeight && rect.top > dropHeight;
        setDropStyle({
          position: "fixed",
          left: `${rect.left}px`,
          width: `${Math.max(rect.width, 160)}px`,
          ...(placeAbove
            ? { bottom: `${window.innerHeight - rect.top + 2}px` }
            : { top: `${rect.bottom + 2}px` }),
        });
      }
      return !prev;
    });
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e) => {
      if (
        triggerRef.current?.contains(e.target) ||
        dropdownRef.current?.contains(e.target)
      )
        return;
      setOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return html`
    <div class="mini-color-picker">
      <button
        ref=${triggerRef}
        type="button"
        class="mini-color-trigger"
        onClick=${handleToggle}
        title=${value || "Choose color"}
      >
        <span
          class="mini-color-swatch"
          style=${{ backgroundColor: resolvedHex }}
        />
      </button>
      ${open &&
      html`
        <div ref=${dropdownRef} class="mini-color-dropdown" style=${dropStyle}>
          ${entries.map(
            ([name, hex]) => html`
              <button
                key=${name}
                type="button"
                class="mini-color-option ${name === value ? "selected" : ""}"
                onClick=${() => handleSelect(name)}
                title=${name}
              >
                <span
                  class="mini-color-dot"
                  style=${{ backgroundColor: hex }}
                />
                <span>${name}</span>
              </button>
            `
          )}
        </div>
      `}
    </div>
  `;
}
