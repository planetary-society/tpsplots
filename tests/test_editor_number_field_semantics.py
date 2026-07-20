"""Static checks for the shared numeric-input machinery (lib/numericText.js).

The controlled numeric-text pattern keeps local raw-text state so in-progress
typing (e.g. "3.") does not collapse, but must re-seed that text when
``value`` changes externally (YAML load, union branch clear, chart-type
remap, series array writes). The machinery lives in ``useNumericText`` and is
shared by NumberField and ReferenceLineBuilder; these checks guard the
ref-based re-sync so it does not regress back to seed-once ``useState``
behavior, and that both consumers actually delegate to it.
"""

from tests.conftest import read_source as _read

_HOOK = "tpsplots/editor/static/js/lib/numericText.js"


def test_hook_tracks_last_emitted_value_with_ref():
    src = _read(_HOOK)
    assert "const emittedRef = useRef(value);" in src


def test_hook_reseeds_raw_on_external_value_change():
    src = _read(_HOOK)
    # Re-sync only when value matches neither the last emitted value nor the
    # currently-typed number (so typing is preserved, external writes are not).
    assert "value !== emittedRef.current && value !== parse(raw)" in src
    assert 'setRaw(value != null ? String(value) : "");' in src


def test_hook_updates_emitted_ref_on_input():
    src = _read(_HOOK)
    assert "emittedRef.current = num;" in src
    assert "emittedRef.current = undefined;" in src


def test_number_field_delegates_to_shared_hook():
    src = _read("tpsplots/editor/static/js/components/fields/NumberField.js")
    assert "useNumericText" in src
    assert "commitEmpty: true" in src


def test_reference_line_builder_delegates_to_shared_hook():
    src = _read("tpsplots/editor/static/js/components/ReferenceLineBuilder.js")
    assert "useNumericText" in src
    # Empty input must never commit (would serialize null into list[float]).
    assert "commitEmpty: false" in src
