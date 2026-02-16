"""Drift detection: every config field must appear in the editor uiSchema.

Similar to test_config_view_sync.py which ensures view kwargs match config
fields, this test ensures every config field has a uiSchema entry (either
explicit or via ui:order).
"""

import pytest

from tpsplots.editor.ui_schema import _get_excluded_fields, get_ui_schema
from tpsplots.models.charts import CONFIG_REGISTRY


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
