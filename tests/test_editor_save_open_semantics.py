"""Static checks for the save/open lift, session undo, and hotkey overhaul.

Source-scan precedent: tests/test_editor_toggle_semantics.py and
tests/test_editor_chart_type_remap.py assert on the editor's JS source directly
(there is no JS test runner in this repo).
"""

from pathlib import Path

from tests.conftest import read_source

_JS_ROOT = Path(__file__).resolve().parent.parent / "tpsplots" / "editor" / "static" / "js"


def _read(rel: str) -> str:
    return read_source(f"tpsplots/editor/static/js/{rel}")


def _all_js_sources() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in _JS_ROOT.rglob("*.js"))


class TestEventBridgeRemoved:
    def test_no_dispatch_event_bridge_anywhere(self):
        """The window.dispatchEvent("editor:save"/"editor:open") bridge is gone —
        hotkeys call the App handlers directly."""
        src = _all_js_sources()
        assert 'dispatchEvent(new Event("editor:save"' not in src
        assert 'dispatchEvent(new Event("editor:open"' not in src
        assert "editor:save" not in src
        assert "editor:open" not in src

    def test_header_no_longer_listens_for_bridge(self):
        header = _read("components/Header.js")
        assert "addEventListener" not in header
        # Header is presentational: it no longer imports the save/list API.
        assert "saveYaml" not in header
        assert "listFiles" not in header


class TestSaveFlowInApp:
    def test_app_owns_save_and_409_overrides(self):
        app = _read("app.js")
        assert "saveYaml" in app
        assert "override_validation" in app
        assert "override_conflict" in app

    def test_save_yaml_accepts_overrides(self):
        api = _read("api.js")
        assert "export async function saveYaml(path, config, overrides = {})" in api

    def test_header_receives_lifted_handlers(self):
        header = _read("components/Header.js")
        for prop in ("onSave", "onSaveAs", "onOpen", "onNew"):
            assert prop in header, f"Header should receive {prop}"


class TestNewAndSaveAs:
    def test_app_has_new_and_save_as(self):
        app = _read("app.js")
        assert "handleNew" in app
        assert "handleSaveAs" in app
        # New chart client-side init + Save-As filename prompt.
        assert '"New Chart"' in app
        assert "window.prompt" in app

    def test_beforeunload_guard(self):
        app = _read("app.js")
        assert "beforeunload" in app


class TestSessionUndo:
    def test_undo_redo_stacks_exist(self):
        app = _read("app.js")
        assert "undoStackRef" in app
        assert "redoStackRef" in app
        assert "MAX_UNDO" in app

    def test_undo_wired_to_hotkeys(self):
        app = _read("app.js")
        assert "onUndo" in app
        assert "onRedo" in app


class TestHotkeys:
    def test_bare_device_keys_removed(self):
        hk = _read("hooks/useHotkeys.js")
        assert 'key === "d"' not in hk
        assert 'key === "m"' not in hk
        assert "onSetDevice" not in hk

    def test_undo_redo_help_added(self):
        hk = _read("hooks/useHotkeys.js")
        assert 'e.key.toLowerCase() === "z"' in hk
        assert "onUndo" in hk
        assert "onRedo" in hk
        assert 'e.key === "?"' in hk
        assert "onToggleHelp" in hk
        assert 'e.key === "Escape"' in hk
