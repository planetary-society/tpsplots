/**
 * TPS color widget.
 * Supports both single color and list-of-colors fields based on schema types.
 */
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { html } from "../lib/html.js";

function normalizeColorToken(input) {
  return typeof input === "string" ? input.trim() : "";
}

function dedupeColors(colors) {
  const cleaned = colors.map(normalizeColorToken).filter(Boolean);
  return [...new Set(cleaned)];
}

function collectAllowedTypes(schema) {
  const types = new Set();
  const pushType = (t) => {
    if (typeof t === "string") types.add(t);
    if (Array.isArray(t)) {
      for (const item of t) {
        if (typeof item === "string") types.add(item);
      }
    }
  };

  pushType(schema?.type);
  const branches = Array.isArray(schema?.anyOf) ? schema.anyOf : [];
  for (const branch of branches) {
    pushType(branch?.type);
  }
  return types;
}

const GROUP_LABELS = { brand: "Brand", neutral: "Neutral", accent: "Accent" };
const GROUP_ORDER = ["brand", "neutral", "accent"];

function ColorSwatchGroups({ tpsColors, colorSemantics, selected, onSwatchClick }) {
  const grouped = useMemo(() => {
    const groups = { brand: [], neutral: [], accent: [] };
    for (const [name, hex] of Object.entries(tpsColors || {})) {
      const meta = colorSemantics?.[name];
      const group = meta?.group || "accent";
      if (groups[group]) {
        groups[group].push({ name, hex, usage: meta?.usage || "" });
      }
    }
    return groups;
  }, [tpsColors, colorSemantics]);

  // If no semantics data, fall back to flat swatch row
  if (!colorSemantics || Object.keys(colorSemantics).length === 0) {
    return html`
      <div class="swatch-row">
        ${Object.entries(tpsColors || {}).map(([name, hex]) => html`
          <button
            key=${name}
            type="button"
            class="swatch ${selected.has(name) ? "selected" : ""}"
            aria-pressed=${selected.has(name)}
            style=${{ backgroundColor: hex }}
            title=${name}
            onClick=${() => onSwatchClick(name)}
          >
            ${selected.has(name) ? html`<span class="swatch-check">\u2713</span>` : null}
          </button>
        `)}
      </div>
    `;
  }

  return html`
    <div class="swatch-groups">
      ${GROUP_ORDER.map(
        (groupKey) =>
          grouped[groupKey]?.length > 0 &&
          html`
            <div key=${groupKey} class="swatch-group swatch-group-${groupKey}">
              <div class="swatch-group-label">${GROUP_LABELS[groupKey]}</div>
              <div class="swatch-row">
                ${grouped[groupKey].map(
                  ({ name, hex, usage }) => html`
                    <div key=${name} class="swatch-item">
                      <button
                        type="button"
                        class="swatch ${groupKey === "brand" ? "swatch-brand" : ""} ${selected.has(name) ? "selected" : ""}"
                        aria-pressed=${selected.has(name)}
                        style=${{ backgroundColor: hex }}
                        title=${usage ? `${name}: ${usage}` : name}
                        onClick=${() => onSwatchClick(name)}
                      >
                        ${selected.has(name) ? html`<span class="swatch-check">\u2713</span>` : null}
                      </button>
                      ${groupKey === "brand" &&
                      html`<span class="swatch-name">${name.split(" ")[0]}</span>`}
                    </div>
                  `
                )}
              </div>
            </div>
          `
      )}
    </div>
  `;
}

export function ColorWidget(props) {
  const { value, onChange, options, schema } = props;
  const tpsColors = options?.tpsColors || {};
  const semanticColors = options?.semanticColors || {};

  const allowedTypes = useMemo(() => collectAllowedTypes(schema), [schema]);
  const supportsArray = allowedTypes.has("array");
  const supportsSingle = !supportsArray || allowedTypes.has("string");
  const initialMode = Array.isArray(value) || (supportsArray && !supportsSingle) ? "multi" : "single";

  const [mode, setMode] = useState(initialMode);
  const [singleInput, setSingleInput] = useState(typeof value === "string" ? value : "");
  const [multiInput, setMultiInput] = useState("");
  const [multiList, setMultiList] = useState(Array.isArray(value) ? dedupeColors(value) : []);
  const modeCacheRef = useRef({
    single: typeof value === "string" ? normalizeColorToken(value) : "",
    multi: Array.isArray(value) ? dedupeColors(value) : [],
  });

  useEffect(() => {
    if (!supportsSingle && supportsArray && mode !== "multi") {
      setMode("multi");
    }
  }, [supportsSingle, supportsArray, mode]);

  useEffect(() => {
    modeCacheRef.current.single = singleInput;
  }, [singleInput]);

  useEffect(() => {
    modeCacheRef.current.multi = multiList;
  }, [multiList]);

  useEffect(() => {
    if (Array.isArray(value)) {
      const nextList = dedupeColors(value);
      setMultiList(nextList);
      modeCacheRef.current.multi = nextList;
      if (supportsArray) setMode("multi");
      setSingleInput(nextList[0] || "");
      modeCacheRef.current.single = nextList[0] || "";
      return;
    }

    if (typeof value === "string") {
      const nextSingle = normalizeColorToken(value);
      setSingleInput(nextSingle);
      modeCacheRef.current.single = nextSingle;
      if (supportsArray && !supportsSingle) {
        const nextList = nextSingle ? [nextSingle] : [];
        setMultiList(nextList);
        modeCacheRef.current.multi = nextList;
      }
      return;
    }

    setSingleInput("");
    modeCacheRef.current.single = "";
    if (!supportsSingle && supportsArray) {
      setMultiList([]);
      modeCacheRef.current.multi = [];
    }
  }, [value, supportsArray, supportsSingle]);

  const commitSingle = useCallback((nextValue) => {
    const normalized = normalizeColorToken(nextValue);
    setSingleInput(normalized);
    onChange(normalized || undefined);
  }, [onChange]);

  const commitMulti = useCallback((nextList) => {
    nextList = dedupeColors(nextList);
    setMultiList(nextList);
    onChange(nextList.length > 0 ? nextList : undefined);
  }, [onChange]);

  const handleSwatchClick = useCallback((name) => {
    if (mode === "multi") {
      const exists = multiList.includes(name);
      const nextList = exists ? multiList.filter((color) => color !== name) : [...multiList, name];
      commitMulti(nextList);
      return;
    }
    commitSingle(name);
  }, [mode, multiList, commitSingle, commitMulti]);

  const handleSingleInput = useCallback((e) => {
    commitSingle(e.target.value);
  }, [commitSingle]);

  const handleModeChange = useCallback((nextMode) => {
    if (nextMode === mode) return;
    setMode(nextMode);

    if (nextMode === "multi") {
      const cachedMulti = modeCacheRef.current.multi;
      const seed = normalizeColorToken(singleInput);
      const baseline = cachedMulti.length > 0 ? cachedMulti : multiList;
      const nextList = dedupeColors(seed ? [seed, ...baseline] : baseline);
      commitMulti(nextList);
      return;
    }

    const cachedSingle = modeCacheRef.current.single;
    const fallback = normalizeColorToken(cachedSingle) || normalizeColorToken(singleInput) || multiList[0] || "";
    commitSingle(fallback);
  }, [mode, singleInput, multiList, commitSingle, commitMulti]);

  const addMultiColor = useCallback((rawValue) => {
    const candidate = normalizeColorToken(rawValue);
    if (!candidate) return;
    if (!multiList.includes(candidate)) {
      commitMulti([...multiList, candidate]);
    }
    setMultiInput("");
  }, [multiList, commitMulti]);

  const removeMultiColor = useCallback((color) => {
    commitMulti(multiList.filter((item) => item !== color));
  }, [multiList, commitMulti]);

  // Resolve display color: check TPS names first, then semantic, then raw
  const resolveColor = (name) => {
    if (!name) return "transparent";
    return tpsColors[name] || semanticColors[name] || name;
  };

  const currentValue = mode === "multi" ? multiInput : singleInput;
  const selected = new Set(mode === "multi" ? multiList : [singleInput].filter(Boolean));
  const previewColor =
    mode === "multi" ? resolveColor(multiList[0] || "") : resolveColor(singleInput);

  return html`
    <div class="color-widget">
      ${supportsArray && supportsSingle && html`
        <div class="color-mode-toggle" role="group" aria-label="Color entry mode">
          <button
            type="button"
            class="color-mode-btn ${mode === "single" ? "active" : ""}"
            aria-pressed=${mode === "single"}
            onClick=${() => handleModeChange("single")}
          >Single</button>
          <button
            type="button"
            class="color-mode-btn ${mode === "multi" ? "active" : ""}"
            aria-pressed=${mode === "multi"}
            onClick=${() => handleModeChange("multi")}
          >Multiple</button>
        </div>
      `}

      <${ColorSwatchGroups}
        tpsColors=${tpsColors}
        colorSemantics=${options?.colorSemantics}
        selected=${selected}
        onSwatchClick=${handleSwatchClick}
      />

      <div class="hex-input-row">
        <span
          class="hex-preview"
          style=${{ backgroundColor: previewColor }}
        />
        <input
          type="text"
          class="hex-input"
          value=${currentValue}
          onInput=${mode === "multi" ? (e) => setMultiInput(e.target.value) : handleSingleInput}
          onKeyDown=${(e) => {
            if (mode === "multi" && e.key === "Enter") {
              e.preventDefault();
              addMultiColor(multiInput);
            }
          }}
          placeholder=${mode === "multi" ? "Add color name or #hex" : "Color name or #hex"}
        />
        ${mode === "multi" && html`
          <button
            type="button"
            class="color-add-btn"
            onClick=${() => addMultiColor(multiInput)}
            disabled=${!normalizeColorToken(multiInput)}
          >Add</button>
        `}
      </div>

      ${mode === "multi" && html`
        <div class="color-chip-row">
          ${multiList.map((color) => html`
            <span key=${color} class="color-chip">
              <span class="color-chip-preview" style=${{ backgroundColor: resolveColor(color) }} />
              <span class="color-chip-label">${color}</span>
              <button
                type="button"
                class="color-chip-remove"
                aria-label=${`Remove ${color}`}
                onClick=${() => removeMultiColor(color)}
              >
                \u00d7
              </button>
            </span>
          `)}
        </div>
      `}
    </div>
  `;
}
