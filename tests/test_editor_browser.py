"""Focused real-browser regressions for the chart editor.

These tests are intentionally opt-in (``pytest -m browser``): Chromium must be
installed for Playwright and the frontend must be able to load React from
esm.sh. Every test gets a fresh browser context, while the editor server uses a
temporary copy of the example YAML directory so no repository YAML can be
written by an interaction.
"""

from __future__ import annotations

import shutil
import socket
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn
import yaml
from playwright.sync_api import Page, expect, sync_playwright

from tpsplots.editor.app import create_editor_app
from tpsplots.editor.session import EditorSession

pytestmark = pytest.mark.browser

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def editor_server(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    """Serve the editor against a disposable copy of ``yaml/examples``."""
    yaml_dir = tmp_path_factory.mktemp("editor-browser") / "examples"
    shutil.copytree(_REPO_ROOT / "yaml" / "examples", yaml_dir)
    protected_path = yaml_dir / "multiline_nasa_major_programs_by_year.yaml"
    protected_text = protected_path.read_text(encoding="utf-8")
    protected_text = "# hand comment\n" + protected_text.replace(
        "chart:\n",
        'chart:\n  annotations:\n    - x: 2010\n      y: 5\n      text: "Test note"\n'
        "  figsize: [12, 7]\n",
        1,
    )
    protected_path.write_text(protected_text, encoding="utf-8")
    defaults_path = yaml_dir / "viking_cost_breakdown_treemap.yaml"
    defaults_text = defaults_path.read_text(encoding="utf-8")
    for explicit_default in (
        "    auto_clean_currency: true\n",
        "  show_labels: true\n",
        "  show_percentages: true\n",
    ):
        defaults_text = defaults_text.replace(explicit_default, "", 1)
    defaults_path.write_text(defaults_text, encoding="utf-8")

    port = _available_port()
    app = create_editor_app(EditorSession(yaml_dir=yaml_dir))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/"
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Editor server did not become ready")

    yield {"url": url, "yaml_dir": yaml_dir}

    server.should_exit = True
    thread.join(timeout=10)
    assert not thread.is_alive(), "Editor server did not stop"


@pytest.fixture
def editor_page(editor_server: dict[str, Any]) -> Iterator[Page]:
    """Open a ready editor page and fail the test on any JS page error."""
    page_errors: list[str] = []
    console_messages: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000})
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console", lambda message: console_messages.append(f"{message.type}: {message.text}")
        )
        page.goto(editor_server["url"], wait_until="domcontentloaded")
        page.wait_for_function("window.__editorReady === true")

        yield page

        context.close()
        browser.close()

    assert not page_errors, (
        "JavaScript page errors:\n"
        + "\n".join(page_errors)
        + "\nConsole:\n"
        + "\n".join(console_messages)
    )


def _active_section(page: Page, label: str) -> None:
    expect(page.locator(".section-chip.active")).to_contain_text(label)


def _input_values(locator: Any) -> list[str]:
    return locator.evaluate_all("elements => elements.map(element => element.value)")


def _open_file(page: Page, filename: str) -> None:
    page.get_by_role("button", name="Open", exact=True).click()
    file_filter = page.locator(".file-menu-filter")
    expect(file_filter).to_be_focused()
    file_filter.fill(filename)
    file_filter.press("Enter")
    expect(page.locator(".header-filename")).to_contain_text(filename)


def _yaml_config(page: Page, expected_text: str) -> dict[str, Any]:
    yaml_button = page.get_by_role("button", name="YAML", exact=True)
    if yaml_button.get_attribute("aria-pressed") != "true":
        yaml_button.click()
    code = page.locator(".yaml-pane-code")
    expect(code).to_contain_text(expected_text, timeout=5_000)
    return yaml.safe_load(code.inner_text())


def test_add_series_keeps_pending_rows_and_correlated_values(editor_page: Page) -> None:
    page = editor_page
    page.locator(".chart-type-select").select_option("line")
    primary = page.locator(".series-axis-group").first
    rows = primary.locator(".series-row")
    add = primary.get_by_role("button", name="+ Add series")

    expect(rows).to_have_count(0)
    add.click()
    expect(rows).to_have_count(1)
    add.click()
    expect(rows).to_have_count(2)

    bindings = primary.locator(".series-row-binding")
    labels = primary.locator(".series-row-label")
    bindings.nth(0).fill("{{First}}")
    bindings.nth(1).fill("{{Second}}")
    labels.nth(0).fill("Alpha")
    labels.nth(1).fill("Beta")

    add.click()
    expect(rows).to_have_count(3)
    labels.nth(2).fill("Pending")
    rows.nth(2).get_by_title("Move up").click()

    assert _input_values(bindings) == ["{{First}}", "", "{{Second}}"]
    assert _input_values(labels) == ["Alpha", "Pending", "Beta"]

    rows.nth(1).get_by_title("Remove series").click()
    assert _input_values(bindings) == ["{{First}}", "{{Second}}"]
    assert _input_values(labels) == ["Alpha", "Beta"]

    config = _yaml_config(page, "{{Second}}")
    assert config["chart"]["y"] == ["{{First}}", "{{Second}}"]
    assert config["chart"]["labels"] == ["Alpha", "Beta"]


def test_area_series_table_exposes_area_styles_and_updates_yaml(editor_page: Page) -> None:
    page = editor_page
    page.locator(".chart-type-select").select_option("area")
    primary = page.locator(".series-axis-group").first
    add = primary.get_by_role("button", name="+ Add series")
    add.click()
    add.click()

    rows = primary.locator(".series-row")
    expect(rows).to_have_count(2)
    bindings = primary.locator(".series-row-binding")
    labels = primary.locator(".series-row-label")
    bindings.nth(0).fill("{{Science}}")
    bindings.nth(1).fill("{{Exploration}}")
    labels.nth(0).fill("Science")
    labels.nth(1).fill("Exploration")

    style = rows.nth(0).locator(".series-row-style")
    style.evaluate("element => { element.open = true; }")
    expect(style).to_contain_text("Line")
    expect(style).to_contain_text("Weight")
    expect(style).to_contain_text("Edge")
    expect(style).to_contain_text("Opacity")

    config = _yaml_config(page, "{{Exploration}}")
    assert config["chart"]["type"] == "area"
    assert config["chart"]["y"] == ["{{Science}}", "{{Exploration}}"]
    assert config["chart"]["labels"] == ["Science", "Exploration"]


def test_scrollspy_keeps_last_section_active_at_scroll_bottom(editor_page: Page) -> None:
    page = editor_page
    panel = page.locator(".form-panel")
    chips = page.locator(".section-chip")

    for index, label in enumerate(("Data", "Chart", "Text & Output")):
        chips.nth(index).click()
        page.wait_for_timeout(700)
        _active_section(page, label)
        assert page.evaluate("document.activeElement?.textContent?.trim()") == label

    for number, label in enumerate(("Data", "Chart", "Text & Output"), start=1):
        page.keyboard.press(f"Alt+{number}")
        page.wait_for_timeout(700)
        _active_section(page, label)
        assert page.evaluate("document.activeElement?.textContent?.trim()") == label

    panel.evaluate("element => { element.scrollTop = element.scrollHeight; }")
    page.wait_for_timeout(250)
    _active_section(page, "Text & Output")


def test_add_option_reveals_group_focuses_control_and_updates_yaml(editor_page: Page) -> None:
    page = editor_page
    page.get_by_role("button", name="Chart", exact=True).click()
    combobox = page.get_by_role("combobox", name="Add chart option")
    combobox.fill("grid")
    expect(page.locator(".add-option-item").first).to_contain_text("Grid")
    combobox.press("Enter")

    field = page.locator('[data-field="grid"]').first
    expect(field).to_be_visible()
    assert field.evaluate("element => element.closest('details')?.open") is True
    assert field.evaluate("element => element.contains(document.activeElement)") is True

    type_select = field.locator("select")
    type_select.select_option("boolean")
    field.locator('input[type="checkbox"]').check()

    config = _yaml_config(page, "grid: true")
    assert config["chart"]["grid"] is True


def test_protected_yaml_survives_unchanged_cross_type_save(
    editor_page: Page, editor_server: dict[str, Any]
) -> None:
    page = editor_page
    filename = "multiline_nasa_major_programs_by_year.yaml"
    path = editor_server["yaml_dir"] / filename
    assert page.locator(".chart-type-select").input_value() == "bar"

    _open_file(page, filename)
    expect(page.locator(".chart-type-select")).to_have_value("line")
    page.get_by_role("button", name="Save", exact=True).click()
    expect(page.locator(".toast")).to_contain_text("Saved")

    saved_text = path.read_text(encoding="utf-8")
    saved = yaml.safe_load(saved_text)
    assert "# hand comment" in saved_text
    assert saved["chart"]["annotations"] == [{"x": 2010, "y": 5, "text": "Test note"}]
    assert saved["chart"]["figsize"] == [12, 7]


def test_default_true_checkboxes_and_currency_cleaning_yaml(editor_page: Page) -> None:
    page = editor_page
    _open_file(page, "viking_cost_breakdown_treemap.yaml")

    expect(page.locator('[data-field="show_labels"] input[type="checkbox"]')).to_be_checked()
    expect(page.locator('[data-field="show_percentages"] input[type="checkbox"]')).to_be_checked()

    currency = page.get_by_label("Auto-clean currency columns", exact=True)
    expect(currency).to_be_checked()
    default_hint = page.locator(".data-params-help").filter(has_text="On by default")
    default_hint.evaluate("element => { element.closest('details').open = true; }")
    expect(default_hint).to_be_visible()

    currency.uncheck()
    config = _yaml_config(page, "auto_clean_currency: false")
    assert config["data"]["params"]["auto_clean_currency"] is False

    currency.check()
    expect(page.locator(".yaml-pane-code")).not_to_contain_text("auto_clean_currency:")
