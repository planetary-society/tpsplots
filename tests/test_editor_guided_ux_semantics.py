"""Static checks for guided UX coverage in the editor."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_binding_step_uses_context_keys_for_controller_bindings():
    src = _read("tpsplots/editor/static/js/components/BindingStep.js")
    assert "const contextKeys = (dataProfile?.context_keys || []).map((key) => String(key));" in src
    assert 'if (lower === "pie_data") {' in src
    assert 'source: "context"' in src
    assert "const referenceNames = useMemo(" in src


def test_binding_step_wires_series_binding_editor_for_line_scatter_y():
    src = _read("tpsplots/editor/static/js/components/BindingStep.js")
    assert "import { SeriesBindingEditor } from \"./SeriesBindingEditor.js\";" in src
    assert "const isSeriesBindingMode = (formData?.type === \"line\" || formData?.type === \"scatter\")" in src
    assert "<${SeriesBindingEditor}" in src
    assert "fieldName=\"y\"" in src


def test_series_binding_editor_supports_add_remove_reorder_and_template_refs():
    src = _read("tpsplots/editor/static/js/components/SeriesBindingEditor.js")
    assert "function templateRef(columnName) {" in src
    assert "const addEmpty = useCallback(() => {" in src
    assert "const move = useCallback(" in src
    assert "const toggleSuggestion = useCallback(" in src
    assert "commitBindings(fieldName, [...bindings, ref], formData, onFormDataChange);" in src


def test_series_editor_includes_markersize_and_alpha_controls():
    src = _read("tpsplots/editor/static/js/components/SeriesEditor.js")
    assert "const hasMarkersize = correlated.includes(\"markersize\");" in src
    assert "const hasAlpha = correlated.includes(\"alpha\");" in src
    assert "\"markersize\"," in src
    assert "\"alpha\"," in src


def test_array_field_supports_boolean_items_via_schema_items_type():
    src = _read("tpsplots/editor/static/js/components/fields/ArrayField.js")
    assert "function schemaItemType(schema) {" in src
    assert "const itemType = resolveItemType(schema, arr);" in src
    assert "itemType === \"boolean\"" in src
    assert "onChange([...arr, false]);" in src


def test_direct_line_labels_widget_is_registered():
    chart_form = _read("tpsplots/editor/static/js/components/ChartForm.js")
    ui_schema = _read("tpsplots/editor/ui_schema.py")
    assert "import { DirectLineLabelsWidget } from \"../widgets/DirectLineLabelsWidget.js\";" in chart_form
    assert "directLineLabels: DirectLineLabelsWidget" in chart_form
    assert "if field_name == \"direct_line_labels\":" in ui_schema
    assert "field_ui[\"ui:widget\"] = \"directLineLabels\"" in ui_schema


def test_data_source_step_wires_custom_params_and_inflation_widgets():
    data_step = _read("tpsplots/editor/static/js/components/DataSourceStep.js")
    ui_schema = _read("tpsplots/editor/ui_schema.py")
    assert "import { DataParamsWidget } from \"../widgets/DataParamsWidget.js\";" in data_step
    assert "import { InflationConfigWidget } from \"../widgets/InflationConfigWidget.js\";" in data_step
    assert "const widgets = useMemo(" in data_step
    assert "availableColumns" in data_step
    assert "widgets=${widgets}" in data_step
    assert "ui[\"params\"][\"ui:widget\"] = \"dataParams\"" in ui_schema
    assert "ui[\"calculate_inflation\"][\"ui:widget\"] = \"inflationConfig\"" in ui_schema


def test_data_params_widget_does_not_use_string_style_props():
    src = _read("tpsplots/editor/static/js/widgets/DataParamsWidget.js")
    assert 'style="' not in src


def test_tiered_visual_design_scopes_advanced_to_visual_fields():
    tiered = _read("tpsplots/editor/static/js/components/TieredVisualDesign.js")
    layout = _read("tpsplots/editor/static/js/components/EditorLayout.js")
    assert "visualFields=${visualDesignFields}" in layout
    assert "visualFields," in tiered
    assert "const all = new Set(visualFields || Object.keys(schema?.properties || {}));" in tiered
