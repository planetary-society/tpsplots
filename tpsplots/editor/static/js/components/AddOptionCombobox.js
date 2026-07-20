/**
 * "Add option…" searchable combobox — the entry point to every chart option
 * not promoted to the essential/common tiers.
 *
 * Replaces the old flat "Advanced" pile of generic inputs: unset options cost
 * zero pixels until added, but every option stays discoverable by searching
 * its name or help text (add-property pattern).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { html } from "../lib/html.js";
import { useListboxNav } from "../hooks/useListboxNav.js";

export function AddOptionCombobox({ options, onAdd }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(q) ||
        opt.name.toLowerCase().includes(q) ||
        (opt.help || "").toLowerCase().includes(q)
    );
  }, [options, query]);

  const commit = useCallback(
    (opt) => {
      if (!opt) return;
      onAdd(opt.name);
      setQuery("");
      setOpen(false);
    },
    [onAdd]
  );

  const { activeIndex, setActiveIndex, onKeyDown: navKeyDown } = useListboxNav({
    length: filtered.length,
    onCommit: (index) => {
      if (open) commit(filtered[index]);
    },
    onClose: () => {
      setOpen(false);
      setQuery("");
    },
  });

  // Highlighted row follows the filter, and clears after a commit empties it.
  useEffect(() => {
    setActiveIndex(0);
  }, [query, setActiveIndex]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "ArrowDown") setOpen(true);
      navKeyDown(e);
    },
    [navKeyDown]
  );

  if (options.length === 0) return null;

  return html`
    <div class="add-option">
      <input
        ref=${inputRef}
        type="text"
        class="add-option-input"
        placeholder="Add option… (${options.length} available)"
        value=${query}
        role="combobox"
        aria-expanded=${open}
        aria-label="Add chart option"
        onInput=${(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus=${() => setOpen(true)}
        onBlur=${() => {
          // Delay so option mousedown wins over blur-close.
          setTimeout(() => setOpen(false), 150);
        }}
        onKeyDown=${handleKeyDown}
      />
      ${open &&
      filtered.length > 0 &&
      html`
        <ul class="add-option-list" role="listbox">
          ${filtered.slice(0, 12).map(
            (opt, i) => html`
              <li
                key=${opt.name}
                class="add-option-item ${i === activeIndex ? "active" : ""}"
                role="option"
                aria-selected=${i === activeIndex}
                onMouseDown=${(e) => {
                  e.preventDefault();
                  commit(opt);
                }}
                onMouseEnter=${() => setActiveIndex(i)}
              >
                <span class="add-option-label">${opt.label}</span>
                ${opt.help && html`<span class="add-option-help">${opt.help}</span>`}
              </li>
            `
          )}
          ${filtered.length > 12 &&
          html`<li class="add-option-more">${filtered.length - 12} more — keep typing</li>`}
        </ul>
      `}
      ${open &&
      filtered.length === 0 &&
      html`<ul class="add-option-list"><li class="add-option-more">No matching options</li></ul>`}
    </div>
  `;
}
