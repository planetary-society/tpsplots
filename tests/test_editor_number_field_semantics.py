"""Static checks for NumberField re-syncing on external value changes.

NumberField keeps local raw-text state so in-progress typing (e.g. "3.")
does not collapse, but it must re-seed that text when ``value`` changes
externally (YAML load, union branch clear, chart-type remap, series array
writes). These checks guard the ref-based re-sync so it does not regress
back to the seed-once ``useState`` behavior.
"""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_number_field_tracks_last_emitted_value_with_ref():
    src = _read("tpsplots/editor/static/js/components/fields/NumberField.js")
    assert "useRef" in src
    assert "const emittedRef = useRef(value);" in src


def test_number_field_reseeds_raw_on_external_value_change():
    src = _read("tpsplots/editor/static/js/components/fields/NumberField.js")
    # Re-sync only when value matches neither the last emitted value nor the
    # currently-typed number (so typing is preserved, external writes are not).
    assert "value !== emittedRef.current && value !== parseNumber(raw, schema)" in src
    assert 'setRaw(value != null ? String(value) : "");' in src


def test_number_field_updates_emitted_ref_on_input():
    src = _read("tpsplots/editor/static/js/components/fields/NumberField.js")
    assert "emittedRef.current = num;" in src
    assert "emittedRef.current = undefined;" in src
