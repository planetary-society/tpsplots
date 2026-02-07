"""Drift detection: every config field must appear in the editor uiSchema.

Similar to test_config_view_sync.py which ensures view kwargs match config
fields, this test ensures every config field has a uiSchema entry (either
explicit or via ui:order).
"""

import pytest

from tpsplots.editor.ui_schema import get_ui_schema
from tpsplots.models.charts import CONFIG_REGISTRY


@pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
def test_all_config_fields_in_ui_order(chart_type):
    """Every field in the config model must appear in ui:order."""
    config_cls = CONFIG_REGISTRY[chart_type]
    ui = get_ui_schema(chart_type)
    ui_order = set(ui.get("ui:order", []))

    for field_name in config_cls.model_fields:
        assert field_name in ui_order, (
            f"Field '{field_name}' in {config_cls.__name__} "
            f"missing from ui:order for chart type '{chart_type}'"
        )


@pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
def test_all_config_fields_in_some_group(chart_type):
    """Every field must belong to a ui:group."""
    config_cls = CONFIG_REGISTRY[chart_type]
    ui = get_ui_schema(chart_type)
    groups = ui.get("ui:groups", [])

    grouped_fields = set()
    for group in groups:
        grouped_fields.update(group["fields"])

    for field_name in config_cls.model_fields:
        assert field_name in grouped_fields, (
            f"Field '{field_name}' in {config_cls.__name__} "
            f"not assigned to any ui:group for chart type '{chart_type}'"
        )
