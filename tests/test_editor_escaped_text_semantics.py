"""Static checks for the escape translation on single-line text inputs.

A single-line ``<input>`` cannot hold a real newline, so users type ``\\n``
the way hand-written YAML spells a line break. Without translation that
sequence reaches matplotlib literally and renders as backslash-n on the
chart. ``lib/escapedText.js`` decodes on input and re-encodes for display so
the stored config always holds a real newline; these checks guard that every
chart-text input keeps both halves of the round trip wired up.
"""

from tests.conftest import read_source as _read

_LIB = "tpsplots/editor/static/js/lib/escapedText.js"

# Inputs whose value is rendered as chart text on one line.
_CONSUMERS = [
    "tpsplots/editor/static/js/components/SeriesTable.js",
    "tpsplots/editor/static/js/components/MetadataSection.js",
    "tpsplots/editor/static/js/components/ReferenceLineBuilder.js",
    "tpsplots/editor/static/js/components/fields/StringField.js",
]


def test_lib_exports_both_directions():
    src = _read(_LIB)
    assert "export function decodeEscapes(text)" in src
    assert "export function encodeEscapes(text)" in src


def test_decode_handles_backslash_runs_pairwise():
    """`\\\\n` is a literal backslash + "n", only a lone `\\n` is a newline."""
    src = _read(_LIB)
    assert "/\\\\+n/g" in src
    assert "slashes % 2 === 1" in src


def test_encode_escapes_backslashes_before_newlines():
    """Order matters: escaping newlines first would double-escape them."""
    src = _read(_LIB)
    encode = src.split("export function encodeEscapes")[1]
    assert encode.index("replace(/\\\\/g") < encode.index("replace(/\\n/g")


def test_consumers_wire_up_both_directions():
    for path in _CONSUMERS:
        src = _read(path)
        assert "decodeEscapes" in src, f"{path} decodes input"
        assert "encodeEscapes" in src, f"{path} re-encodes for display"


def test_string_field_leaves_raw_text_mode_alone():
    """Raw union strings are edited verbatim — no escape translation."""
    src = _read("tpsplots/editor/static/js/components/fields/StringField.js")
    assert 'rawTextMode ? (value ?? "") : encodeEscapes(value ?? "")' in src
    assert "rawTextMode ? handleChange : handleTextChange" in src
