"""Static checks for union-field type switch value preservation."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_union_field_switch_uses_conversion_not_blind_defaults():
    src = _read("tpsplots/editor/static/js/components/fields/UnionField.js")
    assert "function convertValueForType(value, targetType) {" in src
    assert 'if (targetType === "array") {' in src
    assert "if (typeof value === \"string\" && value.trim() !== \"\") return [value];" in src
    assert 'if (targetType === "string") {' in src
    assert "if (Array.isArray(value)) {" in src
    assert "onChange(converted);" in src
    assert "const valueCacheRef = useRef({});" in src
    assert "valueCacheRef.current[currentType] = value;" in src
    assert "const cached = valueCacheRef.current[newType];" in src
