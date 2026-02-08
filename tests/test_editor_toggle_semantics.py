"""Static checks for editor toggle semantics in presentation-layer controls."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_step_headers_support_click_to_collapse_and_pressed_state():
    src = _read("tpsplots/editor/static/js/components/EditorLayout.js")
    assert "onStepChange(isOpen ? null : stepId)" in src
    assert "aria-pressed=${isOpen}" in src


def test_device_toggle_buttons_use_pressed_state():
    src = _read("tpsplots/editor/static/js/components/PreviewPanel.js")
    assert "aria-pressed=${device === \"desktop\"}" in src
    assert "aria-pressed=${device === \"mobile\"}" in src
