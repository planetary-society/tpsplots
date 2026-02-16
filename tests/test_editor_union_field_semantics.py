"""Static checks for union-field type switch value preservation."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_union_field_switch_uses_conversion_not_blind_defaults():
    src = _read("tpsplots/editor/static/js/components/fields/UnionField.js")
    assert "function convertValueForType(value, targetType) {" in src
    assert 'if (targetType === "array") {' in src
    assert 'if (typeof value === "string") return parseStringAsArray(value);' in src
    assert 'if (targetType === "string") {' in src
    assert "if (Array.isArray(value)) {" in src
    assert "onChange(converted);" in src
    assert "const valueCacheRef = useRef({});" in src
    assert "valueCacheRef.current[currentType] = value;" in src
    assert "const cached = valueCacheRef.current[newType];" in src
    assert 'string: "Raw Text",' in src
    assert 'rawTextMode=${currentType === "string"}' in src


def test_union_field_complex_values_convert_without_object_object_strings():
    src = _read("tpsplots/editor/static/js/components/fields/UnionField.js")
    assert "function stringifyForText(value) {" in src
    assert "return JSON.stringify(value);" in src
    assert "function parseStringAsArray(value) {" in src
    assert "const parsed = JSON.parse(trimmed);" in src
    assert "const parts = trimmed.split(\",\").map((item) => item.trim()).filter(Boolean);" in src
    assert "function parseStringAsObject(value) {" in src


def test_raw_text_mode_uses_monospace_input_styling():
    string_src = _read("tpsplots/editor/static/js/components/fields/StringField.js")
    css_src = _read("tpsplots/editor/static/css/editor.css")
    assert 'const inputClass = rawTextMode ? "field-input field-input-mono" : "field-input";' in string_src
    assert "input.field-input-mono," in css_src
    assert "ui-monospace" in css_src
