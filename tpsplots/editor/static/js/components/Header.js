/**
 * Editor header: chart type selector, file name, and file actions.
 *
 * Presentational only. All save/open/new logic lives in app.js (App owns the
 * handlers and the file-menu / help-sheet overlay state); this component just
 * renders buttons that call the handlers it is given. There is no hotkey
 * event bridge — hotkeys call the App handlers directly.
 */
import { useState, useEffect, useMemo, useRef } from "react";
import { html } from "../lib/html.js";
import { useListboxNav } from "../hooks/useListboxNav.js";

const HOTKEYS = [
  ["⌘S", "Save"],
  ["⌘O", "Open"],
  ["⌘Y", "Toggle YAML pane"],
  ["⌘↵", "Re-render preview"],
  ["⌘⇧M", "Toggle device"],
  ["Alt 1–3", "Jump to section"],
  ["⌘Z", "Undo"],
  ["⌘⇧Z", "Redo"],
  ["?", "This shortcut sheet"],
  ["Esc", "Close overlay"],
];

/**
 * Keyboard-shortcut overlay. Rendered by App when helpOpen; closes on backdrop
 * click (Esc / "?" are handled by the global hotkey layer).
 */
export function HotkeySheet(props) {
  const { onClose } = props;
  return html`
    <div class="hotkey-sheet-overlay" onClick=${onClose}>
      <div
        class="hotkey-sheet"
        role="dialog"
        aria-label="Keyboard shortcuts"
        onClick=${(e) => e.stopPropagation()}
      >
        <div class="hotkey-sheet-header">Keyboard shortcuts</div>
        <ul class="hotkey-sheet-list">
          ${HOTKEYS.map(
            ([keys, label]) => html`
              <li key=${label} class="hotkey-sheet-row">
                <kbd class="hotkey-sheet-keys">${keys}</kbd>
                <span class="hotkey-sheet-label">${label}</span>
              </li>
            `
          )}
        </ul>
        <div class="hotkey-sheet-hint">Press Esc or ? to close</div>
      </div>
    </div>
  `;
}

/**
 * Open-file dialog: type-to-filter over the enriched file list (path OR title),
 * recents first, keyboard navigable (up/down/enter/esc). ``files`` items are
 * ``{path, type, title}``; ``recentFiles`` is an ordered list of paths.
 */
export function FileMenu(props) {
  const { files = [], recentFiles = [], onSelect, onClose } = props;
  const [filter, setFilter] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const matches = (f) =>
      !q ||
      f.path.toLowerCase().includes(q) ||
      (f.title || "").toLowerCase().includes(q);
    const matching = files.filter(matches);
    const byPath = new Map(matching.map((f) => [f.path, f]));
    const recentSet = new Set(recentFiles);
    const recents = recentFiles.map((p) => byPath.get(p)).filter(Boolean);
    const rest = matching.filter((f) => !recentSet.has(f.path));
    return { recents, rest };
  }, [files, recentFiles, filter]);

  const flat = useMemo(
    () => [...groups.recents, ...groups.rest],
    [groups]
  );

  const { activeIndex: selected, setActiveIndex: setSelected, onKeyDown } = useListboxNav({
    length: flat.length,
    onCommit: (index) => {
      const f = flat[index];
      if (f) onSelect(f.path);
    },
    onClose,
  });

  // Reset the highlighted row whenever the filtered set changes.
  useEffect(() => {
    setSelected(0);
  }, [filter, setSelected]);

  // `idx` is the row's position in `flat` (recents first), which is what
  // useListboxNav's keyboard selection indexes into — passed in by the caller
  // rather than searched for, so rendering stays linear in the file count.
  const renderRow = (f, idx) => {
    return html`
      <button
        key=${f.path}
        type="button"
        class="file-menu-item ${idx === selected ? "selected" : ""}"
        onClick=${() => onSelect(f.path)}
        onMouseEnter=${() => setSelected(idx)}
      >
        <span class="file-menu-item-path">${f.path}</span>
        ${f.type &&
        html`<span class="file-menu-item-badge">${f.type}</span>`}
        ${f.title &&
        html`<span class="file-menu-item-title">${f.title}</span>`}
      </button>
    `;
  };

  return html`
    <div class="file-menu-overlay" onClick=${onClose}>
      <div class="file-menu" onClick=${(e) => e.stopPropagation()}>
        <div class="file-menu-header">Open YAML File</div>
        <input
          ref=${inputRef}
          class="file-menu-filter"
          type="text"
          placeholder="Filter by name or title…"
          value=${filter}
          onInput=${(e) => setFilter(e.target.value)}
          onKeyDown=${onKeyDown}
        />
        <div class="file-menu-list">
          ${flat.length === 0
            ? html`<div class="file-menu-empty">No matching files</div>`
            : html`
                ${groups.recents.length > 0 &&
                html`
                  <div class="file-menu-group">Recent</div>
                  ${groups.recents.map((f, i) => renderRow(f, i))}
                `}
                ${groups.rest.length > 0 &&
                html`
                  ${groups.recents.length > 0 &&
                  html`<div class="file-menu-group">All files</div>`}
                  ${groups.rest.map((f, i) => renderRow(f, groups.recents.length + i))}
                `}
              `}
        </div>
      </div>
    </div>
  `;
}

export function Header(props) {
  const {
    chartType,
    chartTypes,
    currentFile,
    onChartTypeChange,
    onSave,
    onSaveAs,
    onOpen,
    onNew,
    onToggleHelp,
    saving = false,
    unsavedChanges = false,
    yamlOpen = false,
    onToggleYaml,
  } = props;

  return html`
    <header class="editor-header">
      <div class="header-left">
        <span class="header-logo-badge">
          <img
            class="header-logo-image"
            src="/static/tpsplots-logo-no-text.png"
            alt="tpsplots logo"
          />
        </span>
        <span class="header-logo">tpsplots</span>
      </div>

      <div class="header-center">
        <select
          class="chart-type-select"
          value=${chartType}
          onChange=${(e) => onChartTypeChange(e.target.value)}
        >
          ${chartTypes.map((t) => html`<option key=${t} value=${t}>${t}</option>`)}
        </select>
      </div>

      <div class="header-right">
        <button
          class="btn btn-secondary ${yamlOpen ? "btn-toggled" : ""}"
          onClick=${onToggleYaml}
          aria-pressed=${yamlOpen}
          title="Show the YAML this chart saves as (⌘Y)"
        >YAML</button>
        <button class="btn btn-secondary" onClick=${onNew} title="Start a new chart">New</button>
        <button
          class="btn btn-secondary"
          onClick=${onOpen}
          title="Open a YAML file (⌘O)"
        >Open</button>

        <span class="header-filename">
          ${currentFile || "No file"}
          ${unsavedChanges &&
          html`<span class="header-unsaved-dot" title="Unsaved changes">•</span>`}
        </span>

        <button
          class="btn btn-primary"
          onClick=${onSave}
          disabled=${saving}
          title="Save (⌘S)"
        >
          ${saving ? "Saving…" : "Save"}
        </button>
        <button
          class="btn btn-secondary"
          onClick=${onSaveAs}
          disabled=${saving}
          title="Save to a new file name"
        >Save As</button>
        <button
          class="btn btn-icon"
          onClick=${onToggleHelp}
          title="Keyboard shortcuts (?)"
          aria-label="Keyboard shortcuts"
        >?</button>
      </div>
    </header>
  `;
}
