"""Static checks for chart-type remap behavior in the editor app state."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_line_to_scatter_switch_clears_explicit_linestyle():
    src = _read("tpsplots/editor/static/js/app.js")
    assert "if (previousType !== \"scatter\" && nextType === \"scatter\")" in src
    assert "delete next.linestyle;" in src

