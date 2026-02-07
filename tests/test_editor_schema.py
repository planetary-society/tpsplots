"""Tests for editor JSON Schema and uiSchema generation."""

import pytest

from tpsplots.editor.ui_schema import (
    FIELD_TO_GROUP,
    get_available_chart_types,
    get_chart_type_schema,
    get_ui_schema,
)
from tpsplots.models.charts import CONFIG_REGISTRY


class TestGetChartTypeSchema:
    """Tests for get_chart_type_schema()."""

    def test_returns_valid_schema_for_all_types(self):
        for chart_type in CONFIG_REGISTRY:
            schema = get_chart_type_schema(chart_type)
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_bar_schema_has_expected_fields(self):
        schema = get_chart_type_schema("bar")
        props = schema["properties"]
        assert "title" in props
        assert "output" in props
        assert "categories" in props
        assert "values" in props
        assert "colors" in props
        assert "width" in props

    def test_anyof_null_simplified_for_simple_optional(self):
        """Pydantic's anyOf: [{type: X}, {type: null}] should be simplified."""
        schema = get_chart_type_schema("bar")
        subtitle = schema["properties"]["subtitle"]
        # Should be simplified to just {type: string}
        assert subtitle.get("type") == "string"
        assert "anyOf" not in subtitle

    def test_anyof_collapsed_for_complex_types(self):
        """Multi-type anyOf (e.g. legend: bool|object|string) collapses to best type."""
        schema = get_chart_type_schema("bar")
        legend = schema["properties"]["legend"]
        # anyOf fully collapsed — boolean wins by type priority
        assert "anyOf" not in legend
        assert legend["type"] == "boolean"

    def test_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown chart type"):
            get_chart_type_schema("nonexistent_type")

    def test_required_fields_present(self):
        schema = get_chart_type_schema("bar")
        assert "output" in schema.get("required", [])
        assert "title" in schema.get("required", [])


class TestGetUiSchema:
    """Tests for get_ui_schema()."""

    def test_returns_ui_order(self):
        ui = get_ui_schema("bar")
        assert "ui:order" in ui
        assert isinstance(ui["ui:order"], list)
        assert len(ui["ui:order"]) > 0

    def test_type_field_hidden(self):
        ui = get_ui_schema("bar")
        assert ui.get("type", {}).get("ui:widget") == "hidden"

    def test_color_fields_use_tps_color_widget(self):
        ui = get_ui_schema("bar")
        assert ui.get("colors", {}).get("ui:widget") == "tpsColor"

    def test_ui_groups_present(self):
        ui = get_ui_schema("bar")
        groups = ui.get("ui:groups", [])
        assert len(groups) > 0
        group_names = [g["name"] for g in groups]
        assert "Identity" in group_names
        assert "Bar Styling" in group_names

    def test_identity_group_default_open(self):
        ui = get_ui_schema("bar")
        groups = ui.get("ui:groups", [])
        identity = next(g for g in groups if g["name"] == "Identity")
        assert identity["defaultOpen"] is True

    def test_ui_layout_has_rows(self):
        ui = get_ui_schema("bar")
        layout = ui.get("ui:layout", {})
        assert "rows" in layout

    def test_all_types_generate_ui_schema(self):
        for chart_type in CONFIG_REGISTRY:
            ui = get_ui_schema(chart_type)
            assert "ui:order" in ui
            assert "ui:groups" in ui


class TestGetAvailableChartTypes:
    def test_returns_all_registered_types(self):
        types = get_available_chart_types()
        assert set(types) == set(CONFIG_REGISTRY.keys())

    def test_returns_sorted(self):
        types = get_available_chart_types()
        assert types == sorted(types)


class TestFieldToGroupMapping:
    """Every config field should have a group mapping."""

    @pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
    def test_all_fields_have_group_or_are_chart_specific(self, chart_type):
        config_cls = CONFIG_REGISTRY[chart_type]
        for field_name in config_cls.model_fields:
            # Either mapped to a known group or will end up in Chart-Specific
            group = FIELD_TO_GROUP.get(field_name)
            if group is None:
                # Acceptable — will go to Chart-Specific group
                pass
            else:
                assert isinstance(group, str)
