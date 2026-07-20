"""Static checks for editor toggle semantics in presentation-layer controls."""

from tests.conftest import read_source as _read


def test_section_nav_supports_scrollspy_and_keyboard_focus():
    """The flattened layout replaces the gated accordion: nav chips must both
    scroll to and FOCUS the section heading (keyboard/AT users), and the
    scrollspy must observe against the form panel as its root."""
    src = _read("tpsplots/editor/static/js/components/EditorLayout.js")
    assert "IntersectionObserver" in src
    assert 'querySelector("h3")?.focus?.()' in src
    assert 'tabindex="-1"' in src
    assert "scrollIntoView" in src


def test_device_toggle_buttons_use_pressed_state():
    src = _read("tpsplots/editor/static/js/components/PreviewPanel.js")
    assert "aria-pressed=${device === d}" in src
    # All three output devices are offered, social included.
    assert '"desktop", "mobile", "social"' in src


def test_yaml_toggle_reflects_pressed_state():
    src = _read("tpsplots/editor/static/js/components/Header.js")
    assert "aria-pressed=${yamlOpen}" in src
