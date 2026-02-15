"""Tests for editor JSON Schema and uiSchema generation."""

import pytest

from tpsplots.editor.ui_schema import (
    get_available_chart_types,
    get_chart_type_schema,
    get_data_ui_schema,
    get_editor_hints,
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

    def test_anyof_preserved_for_multi_type_unions(self):
        """Multi-type anyOf (e.g. legend: bool|object|string) preserves branches (null stripped)."""
        schema = get_chart_type_schema("bar")
        legend = schema["properties"]["legend"]
        # anyOf preserved with null branch stripped
        assert "anyOf" in legend
        branch_types = [b.get("type") for b in legend["anyOf"]]
        assert "boolean" in branch_types
        assert "object" in branch_types
        assert "string" in branch_types
        assert "null" not in branch_types

    def test_grid_schema_preserves_anyof(self):
        """grid: bool | dict | str | None should preserve multi-type anyOf (null stripped)."""
        schema = get_chart_type_schema("bar")
        grid = schema["properties"]["grid"]
        # Multi-type union: anyOf preserved with null stripped
        assert "anyOf" in grid
        branch_types = [b.get("type") for b in grid["anyOf"]]
        assert "boolean" in branch_types
        assert "null" not in branch_types

    def test_fiscal_year_ticks_schema(self):
        """fiscal_year_ticks (when present) should be boolean with default null."""
        # Only line charts have fiscal_year_ticks
        schema = get_chart_type_schema("line")
        props = schema["properties"]
        if "fiscal_year_ticks" in props:
            fyt = props["fiscal_year_ticks"]
            assert fyt.get("type") == "boolean"

    def test_no_null_branches_in_any_schema(self):
        """No schema should have null branches in anyOf after processing."""
        for chart_type in CONFIG_REGISTRY:
            schema = get_chart_type_schema(chart_type)
            for field_name, prop in schema.get("properties", {}).items():
                if "anyOf" in prop:
                    branch_types = [b.get("type") for b in prop["anyOf"]]
                    assert "null" not in branch_types, (
                        f"{chart_type}.{field_name} has null branch in anyOf: {branch_types}"
                    )

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
        from tpsplots.editor.ui_schema import _EDITOR_EXCLUDED_TYPES

        types = get_available_chart_types()
        assert set(types) == set(CONFIG_REGISTRY.keys()) - _EDITOR_EXCLUDED_TYPES

    def test_returns_sorted(self):
        types = get_available_chart_types()
        assert types == sorted(types)


class TestEditorHints:
    def test_us_map_pie_primary_binding_is_pie_data(self):
        hints = get_editor_hints("us_map_pie")
        assert hints["primary_binding_fields"] == ["pie_data"]

    def test_scatter_schema_and_visual_design_exclude_line_only_fields(self):
        scatter_schema = get_chart_type_schema("scatter")
        line_schema = get_chart_type_schema("line")

        assert "direct_line_labels" not in scatter_schema["properties"]
        assert "direct_line_labels" in line_schema["properties"]
        assert "linestyle" not in scatter_schema["properties"]
        assert "linestyle" in line_schema["properties"]
        assert "linewidth" not in scatter_schema["properties"]
        assert "linewidth" in line_schema["properties"]

        scatter_hints = get_editor_hints("scatter")
        line_hints = get_editor_hints("line")
        assert "direct_line_labels" not in scatter_hints["step_field_map"]["visual_design"]
        assert "direct_line_labels" in line_hints["step_field_map"]["visual_design"]
        assert "linestyle" not in scatter_hints["step_field_map"]["visual_design"]
        assert "linestyle" in line_hints["step_field_map"]["visual_design"]
        assert "linewidth" not in scatter_hints["step_field_map"]["visual_design"]
        assert "linewidth" in line_hints["step_field_map"]["visual_design"]


class TestDataUiSchema:
    def test_data_widgets_registered_for_complex_fields(self):
        ui = get_data_ui_schema()
        assert ui["params"]["ui:widget"] == "dataParams"
        assert ui["calculate_inflation"]["ui:widget"] == "inflationConfig"


class TestFieldToGroupMapping:
    """Every config field should resolve to a named group."""

    @pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
    def test_all_fields_resolve_to_named_group(self, chart_type):
        from tpsplots.editor.ui_schema import _get_field_group

        config_cls = CONFIG_REGISTRY[chart_type]
        for field_name in config_cls.model_fields:
            group = _get_field_group(field_name, config_cls, chart_type)
            assert isinstance(group, str)
            assert group != "", f"{chart_type}.{field_name} resolved to empty group"

    @pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
    def test_no_chart_specific_group_in_ui_schema(self, chart_type):
        """No chart type should produce a 'Chart-Specific' group after the semantic refactor."""
        ui = get_ui_schema(chart_type)
        group_names = [g["name"] for g in ui.get("ui:groups", [])]
        assert "Chart-Specific" not in group_names, (
            f"{chart_type} still has a 'Chart-Specific' group: "
            f"{[g for g in ui['ui:groups'] if g['name'] == 'Chart-Specific']}"
        )

    @pytest.mark.parametrize("chart_type", list(CONFIG_REGISTRY.keys()))
    def test_advanced_group_has_few_fields(self, chart_type):
        """The 'Advanced' fallback group should have at most 3 fields per chart type."""
        ui = get_ui_schema(chart_type)
        for group in ui.get("ui:groups", []):
            if group["name"] == "Advanced":
                assert len(group["fields"]) <= 3, (
                    f"{chart_type} 'Advanced' group has {len(group['fields'])} fields "
                    f"(max 3): {group['fields']}"
                )


class TestDualYAxisEditorSupport:
    """Tests for dual y-axis field registration in the editor."""

    def test_line_right_axis_group_exists(self):
        ui = get_ui_schema("line")
        group_names = [g["name"] for g in ui.get("ui:groups", [])]
        assert "Right Y-Axis" in group_names

    def test_right_axis_fields_in_correct_group(self):
        ui = get_ui_schema("line")
        right_axis_group = next(g for g in ui["ui:groups"] if g["name"] == "Right Y-Axis")
        assert "ylim_right" in right_axis_group["fields"]
        assert "ylabel_right" in right_axis_group["fields"]
        assert "y_tick_format_right" in right_axis_group["fields"]
        assert "scale_right" in right_axis_group["fields"]

    def test_y_right_in_primary_binding_fields(self):
        hints = get_editor_hints("line")
        assert "y_right" in hints["primary_binding_fields"]

    def test_scatter_y_right_in_primary_binding_fields(self):
        hints = get_editor_hints("scatter")
        assert "y_right" in hints["primary_binding_fields"]

    def test_secondary_trigger_in_editor_hints(self):
        hints = get_editor_hints("line")
        correlated = hints["series_correlated_fields"]
        assert correlated["secondary_trigger_field"] == "y_right"

    def test_scatter_secondary_trigger_in_editor_hints(self):
        hints = get_editor_hints("scatter")
        correlated = hints["series_correlated_fields"]
        assert correlated["secondary_trigger_field"] == "y_right"

    def test_scatter_correlated_excludes_linestyle_linewidth(self):
        """Scatter correlated fields should not include linestyle/linewidth."""
        hints = get_editor_hints("scatter")
        correlated = hints["series_correlated_fields"]["correlated"]
        assert "linestyle" not in correlated
        assert "linewidth" not in correlated

    def test_right_axis_fields_in_common_tier(self):
        hints = get_editor_hints("line")
        common = hints["field_tiers"]["common"]
        for field in ["ylim_right", "ylabel_right", "scale_right", "y_tick_format_right"]:
            assert field in common, f"{field} not in common tier"

    def test_y_right_is_optional_binding(self):
        """y_right must be in OPTIONAL_BINDING_FIELDS so preflight doesn't require it."""
        from tpsplots.editor.ui_schema import OPTIONAL_BINDING_FIELDS

        assert "y_right" in OPTIONAL_BINDING_FIELDS
