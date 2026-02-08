/**
 * Input that renders template refs ({{...}}) as an inline chip overlay.
 * Double-click the chip to enter raw text editing mode.
 */
import { useCallback, useEffect, useRef, useState, createElement } from "react";
import htm from "htm";

import { isTemplateReference } from "./templateRefUtils.js";
import { TemplateRefChip } from "./TemplateRefChip.js";

const html = htm.bind(createElement);

export function TemplateChipInput({
  id,
  name,
  type = "text",
  inputMode,
  className = "",
  value,
  placeholder,
  onInput,
  onChange,
  onBlur,
  onKeyDown,
}) {
  const inputRef = useRef(null);
  const [isEditing, setIsEditing] = useState(false);
  const stringValue = value != null ? String(value) : "";
  const isTemplate = isTemplateReference(stringValue);
  const showChip = isTemplate && !isEditing;

  useEffect(() => {
    if (!isTemplate) setIsEditing(false);
  }, [isTemplate]);

  const focusInput = useCallback(() => {
    if (!inputRef.current) return;
    inputRef.current.focus();
  }, []);

  const enableEditing = useCallback(() => {
    setIsEditing(true);
    requestAnimationFrame(() => {
      if (!inputRef.current) return;
      inputRef.current.focus();
      inputRef.current.select();
    });
  }, []);

  const handleBlur = useCallback(
    (e) => {
      setIsEditing(false);
      onBlur?.(e);
    },
    [onBlur]
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (
        showChip &&
        (e.key.length === 1 ||
          e.key === "Backspace" ||
          e.key === "Delete" ||
          e.key === "Enter")
      ) {
        setIsEditing(true);
      }
      onKeyDown?.(e);
    },
    [onKeyDown, showChip]
  );

  const classes = `template-chip-input ${showChip ? "template-chip-input--masked" : ""} ${className}`;

  return html`
    <div class=${`template-chip-input-wrap ${showChip ? "is-chip" : ""}`}>
      <input
        ref=${inputRef}
        id=${id}
        name=${name}
        type=${type}
        inputMode=${inputMode}
        class=${classes}
        value=${stringValue}
        onInput=${onInput}
        onChange=${onChange}
        onBlur=${handleBlur}
        onKeyDown=${handleKeyDown}
        placeholder=${placeholder}
      />
      ${showChip &&
      html`
        <button
          type="button"
          class="template-chip-overlay"
          title="Template reference. Double-click to edit."
          onMouseDown=${(e) => {
            e.preventDefault();
            focusInput();
          }}
          onDoubleClick=${enableEditing}
        >
          <${TemplateRefChip} value=${stringValue} />
        </button>
      `}
    </div>
  `;
}
