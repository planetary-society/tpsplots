"""Static checks for multi-color behavior in the editor color widget."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_color_widget_supports_schema_driven_multi_mode():
    src = _read("tpsplots/editor/static/js/widgets/ColorWidget.js")
    assert 'const supportsArray = allowedTypes.has("array");' in src
    assert 'const [mode, setMode] = useState(initialMode);' in src
    assert 'if (mode === "multi") {' in src
    assert "onChange(nextList.length > 0 ? nextList : undefined);" in src


def test_schema_form_passes_effective_schema_to_custom_widgets():
    src = _read("tpsplots/editor/static/js/components/SchemaForm.js")
    assert "schema=${effectiveSchema}" in src


def test_color_widget_caches_values_per_mode_for_toggle_roundtrips():
    src = _read("tpsplots/editor/static/js/widgets/ColorWidget.js")
    assert "const modeCacheRef = useRef({" in src
    assert "modeCacheRef.current.single = singleInput;" in src
    assert "modeCacheRef.current.multi = multiList;" in src
    assert "const cachedMulti = modeCacheRef.current.multi;" in src
    assert "const cachedSingle = modeCacheRef.current.single;" in src
