"""Drift detection: every config field must appear in the editor uiSchema.

Similar to test_config_view_sync.py which ensures view kwargs match config
fields, this test ensures every config field has a uiSchema entry (either
explicit or via ui:order).
"""

import pytest

from tests.conftest import read_source
from tpsplots.editor.ui_schema import (
    _get_excluded_fields,
    get_available_chart_types,
    get_editor_hints,
    get_ui_schema,
)
from tpsplots.models.charts import CONFIG_REGISTRY

# Source of the metadata form section, scanned for rendered annotation fields
# (source-scan precedent: tests/test_config_view_sync.py).
_METADATA_SECTION_JS = "tpsplots/editor/static/js/components/MetadataSection.js"


@pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
def test_all_config_fields_in_ui_order(chart_type):
    """Every non-excluded field in the config model must appear in ui:order."""
    config_cls = CONFIG_REGISTRY[chart_type]
    excluded = _get_excluded_fields(config_cls)
    ui = get_ui_schema(chart_type)
    ui_order = set(ui.get("ui:order", []))

    for field_name in config_cls.model_fields:
        if field_name in excluded:
            continue
        assert field_name in ui_order, (
            f"Field '{field_name}' in {config_cls.__name__} "
            f"missing from ui:order for chart type '{chart_type}'"
        )


@pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
def test_all_config_fields_in_some_group(chart_type):
    """Every non-excluded field must belong to a ui:group."""
    config_cls = CONFIG_REGISTRY[chart_type]
    excluded = _get_excluded_fields(config_cls)
    ui = get_ui_schema(chart_type)
    groups = ui.get("ui:groups", [])

    grouped_fields = set()
    for group in groups:
        grouped_fields.update(group["fields"])

    for field_name in config_cls.model_fields:
        if field_name in excluded:
            continue
        assert field_name in grouped_fields, (
            f"Field '{field_name}' in {config_cls.__name__} "
            f"not assigned to any ui:group for chart type '{chart_type}'"
        )


@pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
def test_excluded_fields_absent_from_schema(chart_type):
    """Excluded fields must not appear in ui:order or any ui:group."""
    config_cls = CONFIG_REGISTRY[chart_type]
    excluded = _get_excluded_fields(config_cls)
    ui = get_ui_schema(chart_type)
    ui_order = set(ui.get("ui:order", []))

    grouped_fields = set()
    for group in ui.get("ui:groups", []):
        grouped_fields.update(group["fields"])

    for field_name in excluded:
        assert field_name not in ui_order, (
            f"Excluded field '{field_name}' should not be in ui:order for '{chart_type}'"
        )
        assert field_name not in grouped_fields, (
            f"Excluded field '{field_name}' should not be in any ui:group for '{chart_type}'"
        )


@pytest.mark.parametrize("chart_type", get_available_chart_types())
def test_annotation_fields_rendered_in_metadata_section(chart_type):
    """Every annotation-step field must be rendered by MetadataSection.js.

    The backend routes identity fields (eyebrow, title, subtitle, note, source,
    output) to the ``annotation_output`` step via ``get_editor_hints``. The
    editor's MetadataSection is the sole component that renders that step, so
    each such field must be wired through its ``handleChange`` call. This guards
    against the exact gap that shipped once: eyebrow/note existed on the config
    model and were routed to the annotation step, but the GUI never exposed them.

    Match pattern (stable): the field name as the first quoted argument to
    ``handleChange(...)``, e.g. ``handleChange("eyebrow"`` — this is the write
    path, present only when the input is both rendered and wired.
    """
    annotation_fields = get_editor_hints(chart_type)["step_field_map"]["annotation_output"]
    source = read_source(_METADATA_SECTION_JS)

    for field_name in annotation_fields:
        needle = f'handleChange("{field_name}"'
        assert needle in source, (
            f"Annotation field '{field_name}' (routed to the annotation step for "
            f"chart type '{chart_type}') is not rendered in MetadataSection.js. "
            f"Expected to find {needle!r} in the component source."
        )
