/**
 * TPS Color palette widget for RJSF.
 * Shows brand color swatches + hex input.
 */
import { useState, useCallback, createElement } from "react";
import htm from "htm";

const html = htm.bind(createElement);

export function ColorWidget(props) {
  const { value, onChange, options } = props;
  const tpsColors = options?.tpsColors || {};
  const semanticColors = options?.semanticColors || {};

  const [hexInput, setHexInput] = useState(value || "");

  const handleSwatchClick = useCallback((name) => {
    onChange(name);
    setHexInput(name);
  }, [onChange]);

  const handleHexChange = useCallback((e) => {
    const val = e.target.value;
    setHexInput(val);
    onChange(val);
  }, [onChange]);

  // Resolve display color: check TPS names first, then semantic, then raw
  const resolveColor = (name) => {
    if (!name) return "transparent";
    return tpsColors[name] || semanticColors[name] || name;
  };

  const currentHex = resolveColor(value);

  return html`
    <div class="color-widget">
      <div class="swatch-row">
        ${Object.entries(tpsColors).map(([name, hex]) => html`
          <button
            key=${name}
            type="button"
            class="swatch ${value === name ? "selected" : ""}"
            style=${{ backgroundColor: hex }}
            title=${name}
            onClick=${() => handleSwatchClick(name)}
          >
            ${value === name ? html`<span class="swatch-check">\u2713</span>` : null}
          </button>
        `)}
      </div>

      <div class="hex-input-row">
        <span
          class="hex-preview"
          style=${{ backgroundColor: currentHex }}
        />
        <input
          type="text"
          class="hex-input"
          value=${hexInput}
          onInput=${handleHexChange}
          placeholder="Color name or #hex"
        />
      </div>
    </div>
  `;
}
