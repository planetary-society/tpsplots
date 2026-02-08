"""Generate JSON Schema and uiSchema for the chart editor forms."""

from __future__ import annotations

from typing import Any

from tpsplots.models.charts import CONFIG_REGISTRY
from tpsplots.models.data_sources import DataSourceConfig
from tpsplots.models.mixins import (
    AxisMixin,
    BarStylingMixin,
    GridMixin,
    LegendMixin,
    ScaleMixin,
    SortMixin,
    TickFormatMixin,
    ValueDisplayMixin,
)

# ---------------------------------------------------------------------------
# Field → group mapping (built from mixin model_fields introspection)
# ---------------------------------------------------------------------------

_MIXIN_GROUPS: list[tuple[str, type]] = [
    ("Bar Styling", BarStylingMixin),
    ("Value Labels", ValueDisplayMixin),
    ("Sort", SortMixin),
    ("Scale", ScaleMixin),
    ("Tick Format", TickFormatMixin),
    ("Legend", LegendMixin),
    ("Grid", GridMixin),
    ("Axis", AxisMixin),
]

# Identity group uses fields from ChartConfigBase
_IDENTITY_FIELDS = {"type", "output", "title", "subtitle", "source"}

# System config fields excluded from the schema entirely.
# These are TPS brand constants (figsize, dpi) or pipeline internals
# (export_data, matplotlib_config, line.data DataFrame reference) that are not user-configurable in the
# editor. Stripping them from the JSON schema (not just hiding) prevents
# RJSF from creating form elements or injecting empty defaults.
_EXCLUDED_FIELDS = {"figsize", "dpi", "export_data", "matplotlib_config", "data"}


def _get_excluded_fields(config_cls: type) -> set[str]:
    """Return fields to exclude from the editor for a given config class.

    Keeps only static system-level exclusions.
    """
    _ = config_cls
    return set(_EXCLUDED_FIELDS)


# Build flat lookup: field_name → group_name
FIELD_TO_GROUP: dict[str, str] = {}
for _group_name, _mixin_cls in _MIXIN_GROUPS:
    for _field_name in _mixin_cls.model_fields:
        FIELD_TO_GROUP[_field_name] = _group_name

for _field_name in _IDENTITY_FIELDS:
    FIELD_TO_GROUP[_field_name] = "Identity"

# ---------------------------------------------------------------------------
# Per-chart-type field → group mapping for non-mixin fields.
# Data binding fields (x, y, categories, values, etc.) are filtered to
# Step 2 and excluded here — they never appear in Step 3 groups.
# ---------------------------------------------------------------------------

_CHART_FIELD_GROUPS: dict[str, dict[str, str]] = {
    "bar": {
        "categories": "Data Bindings",
        "values": "Data Bindings",
        "colors": "Colors",
        "positive_color": "Colors",
        "negative_color": "Colors",
    },
    "donut": {
        "values": "Data Bindings",
        "labels": "Data Bindings",
        "colors": "Colors",
        "hole_size": "Donut Shape",
        "center_text": "Donut Shape",
        "center_color": "Donut Shape",
        "wedgeprops": "Donut Shape",
        "show_percentages": "Labels",
        "label_wrap_length": "Labels",
        "label_distance": "Labels",
    },
    "grouped_bar": {
        "categories": "Data Bindings",
        "groups": "Data Bindings",
        "colors": "Colors",
        "labels": "Labels",
        "width": "Bar Styling",
        "alpha": "Bar Styling",
        "edgecolor": "Bar Styling",
        "linewidth": "Bar Styling",
        "value_prefix": "Value Labels",
        "show_yticks": "Axis",
    },
    "line": {
        "x": "Data Bindings",
        "y": "Data Bindings",
        "color": "Line Styling",
        "linestyle": "Line Styling",
        "linewidth": "Line Styling",
        "marker": "Line Styling",
        "markersize": "Line Styling",
        "alpha": "Line Styling",
        "labels": "Labels",
        "series_types": "Labels",
        "direct_line_labels": "Labels",
        "hlines": "Reference Lines",
        "hline_colors": "Reference Lines",
        "hline_styles": "Reference Lines",
        "hline_widths": "Reference Lines",
        "hline_labels": "Reference Lines",
        "hline_alpha": "Reference Lines",
        "hline_label_position": "Reference Lines",
        "hline_label_offset": "Reference Lines",
        "hline_label_fontsize": "Reference Lines",
        "hline_label_bbox": "Reference Lines",
        "xticks": "Custom Ticks",
        "xticklabels": "Custom Ticks",
        "data": "Advanced",
        "series_overrides": "Advanced",
    },
    "scatter": {
        "x": "Data Bindings",
        "y": "Data Bindings",
        "color": "Point Styling",
        "linestyle": "Point Styling",
        "linewidth": "Point Styling",
        "marker": "Point Styling",
        "markersize": "Point Styling",
        "alpha": "Point Styling",
        "labels": "Labels",
        "series_types": "Labels",
        "direct_line_labels": "Labels",
        "hlines": "Reference Lines",
        "hline_colors": "Reference Lines",
        "hline_styles": "Reference Lines",
        "hline_widths": "Reference Lines",
        "hline_labels": "Reference Lines",
        "hline_alpha": "Reference Lines",
        "hline_label_position": "Reference Lines",
        "hline_label_offset": "Reference Lines",
        "hline_label_fontsize": "Reference Lines",
        "hline_label_bbox": "Reference Lines",
        "xticks": "Custom Ticks",
        "xticklabels": "Custom Ticks",
        "data": "Advanced",
        "series_overrides": "Advanced",
    },
    "lollipop": {
        "categories": "Data Bindings",
        "start_values": "Data Bindings",
        "end_values": "Data Bindings",
        "colors": "Colors",
        "marker_size": "Stem Styling",
        "line_width": "Stem Styling",
        "marker_style": "Stem Styling",
        "linestyle": "Stem Styling",
        "alpha": "Stem Styling",
        "start_marker_style": "Endpoint Markers",
        "end_marker_style": "Endpoint Markers",
        "start_marker_size": "Endpoint Markers",
        "end_marker_size": "Endpoint Markers",
        "start_marker_color": "Endpoint Markers",
        "end_marker_color": "Endpoint Markers",
        "start_marker_edgecolor": "Endpoint Markers",
        "end_marker_edgecolor": "Endpoint Markers",
        "start_marker_edgewidth": "Endpoint Markers",
        "end_marker_edgewidth": "Endpoint Markers",
        "value_labels": "Value Labels",
        "range_labels": "Value Labels",
        "start_value_labels": "Value Labels",
        "end_value_labels": "Value Labels",
        "value_format": "Value Labels",
        "value_suffix": "Value Labels",
        "range_format": "Value Labels",
        "range_suffix": "Value Labels",
        "category_wrap_length": "Category Display",
        "y_axis_position": "Category Display",
        "y_tick_marker": "Category Display",
        "y_tick_color": "Category Display",
        "hide_y_spine": "Category Display",
    },
    "stacked_bar": {
        "categories": "Data Bindings",
        "values": "Data Bindings",
        "colors": "Colors",
        "labels": "Labels",
        "stack_labels": "Stack Totals",
        "stack_label_format": "Stack Totals",
        "stack_label_suffix": "Stack Totals",
        "value_threshold": "Value Labels",
        "bottom_values": "Advanced",
    },
    "us_map_pie": {
        "state_data": "Data Bindings",
        "pie_values": "Data Bindings",
        "pie_data": "Data Bindings",
        "pie_size_column": "Pie Sizing",
        "base_pie_size": "Pie Sizing",
        "max_pie_size": "Pie Sizing",
        "min_pie_size": "Pie Sizing",
        "show_pie_labels": "Pie Display",
        "show_percentages": "Pie Display",
        "legend_location": "Pie Display",
        "pie_edge_color": "Pie Display",
        "pie_edge_width": "Pie Display",
        "custom_locations": "Map Settings",
        "show_state_boundaries": "Map Settings",
        "auto_expand_bounds": "Map Settings",
        "padding_factor": "Map Settings",
        "offset_line_color": "Offset Lines",
        "offset_line_style": "Offset Lines",
        "offset_line_width": "Offset Lines",
    },
    "line_subplots": {
        "subplot_data": "Data Bindings",
        "grid_shape": "Subplot Layout",
        "shared_x": "Subplot Layout",
        "shared_y": "Subplot Layout",
        "shared_legend": "Subplot Layout",
        "legend_position": "Subplot Layout",
        "subplot_title_size": "Subplot Layout",
        "xticks": "Custom Ticks",
        "xticklabels": "Custom Ticks",
    },
    "waffle": {
        "values": "Data Bindings",
        "colors": "Colors",
        "labels": "Labels",
        "rows": "Waffle Grid",
        "columns": "Waffle Grid",
        "vertical": "Waffle Grid",
        "starting_location": "Waffle Grid",
        "interval_ratio_x": "Waffle Grid",
        "interval_ratio_y": "Waffle Grid",
        "pywaffle_config": "Advanced",
    },
}


def _get_field_group(field_name: str, config_cls: type, chart_type: str = "") -> str:
    """Return the UI group for a field, checking mixin inheritance.

    A field is assigned to a mixin group only when *config_cls* actually
    inherits from that mixin.  Identity fields are always matched by name.
    Chart-type-specific fields are resolved via ``_CHART_FIELD_GROUPS``.
    Everything else falls through to "Advanced".
    """
    if field_name in _IDENTITY_FIELDS:
        return "Identity"
    for group_name, mixin_cls in _MIXIN_GROUPS:
        if issubclass(config_cls, mixin_cls) and field_name in mixin_cls.model_fields:
            return group_name
    # Per-chart-type semantic groups
    if chart_type and chart_type in _CHART_FIELD_GROUPS:
        group = _CHART_FIELD_GROUPS[chart_type].get(field_name)
        if group:
            return group
    return "Advanced"


# Ordered group names for the UI
GROUP_ORDER = [
    "Identity",
    "Data Bindings",
    "Bar Styling",
    "Colors",
    "Line Styling",
    "Point Styling",
    "Stem Styling",
    "Endpoint Markers",
    "Donut Shape",
    "Waffle Grid",
    "Pie Sizing",
    "Pie Display",
    "Map Settings",
    "Offset Lines",
    "Subplot Layout",
    "Value Labels",
    "Stack Totals",
    "Labels",
    "Category Display",
    "Reference Lines",
    "Sort",
    "Scale",
    "Tick Format",
    "Custom Ticks",
    "Legend",
    "Grid",
    "Axis",
    "Advanced",
]

# Fields hidden in Phase 1 (data bindings handled separately)
_HIDDEN_FIELDS = {"type"}

# Color fields that should use the tpsColor widget
_COLOR_FIELDS = {
    "colors",
    "color",
    "positive_color",
    "negative_color",
    "edgecolor",
    "value_color",
    "center_color",
    "start_marker_color",
    "end_marker_color",
    "start_marker_edgecolor",
    "end_marker_edgecolor",
    "hline_colors",
    "pie_edge_color",
    "offset_line_color",
    "y_tick_color",
}

# Fields that should display inline as a row (pairs)
_INLINE_ROWS = [
    ("xlim", "ylim"),
    ("xlabel", "ylabel"),
    ("x_tick_format", "y_tick_format"),
]

# Primary binding fields shown first in guided editor flows.
PRIMARY_BINDING_FIELDS: dict[str, list[str]] = {
    "line": ["x", "y"],
    "scatter": ["x", "y"],
    "bar": ["categories", "values"],
    "grouped_bar": ["categories", "groups"],
    "stacked_bar": ["categories", "values"],
    "lollipop": ["categories", "start_values", "end_values"],
    "donut": ["labels", "values"],
    "waffle": ["values"],
    "us_map_pie": ["state_data", "pie_values"],
    "line_subplots": ["subplot_data"],
}

# ---------------------------------------------------------------------------
# Field tiers: frequency-based prioritisation for progressive disclosure.
# "essential" = 60%+ real-world usage → always visible in Step 3.
# "common"    = 20-60% usage → one-click expand.
# Everything else falls through to "advanced" (collapsed).
# ---------------------------------------------------------------------------

FIELD_TIERS: dict[str, dict[str, list[str]]] = {
    "line": {
        "essential": ["color", "labels", "scale", "legend", "xlim", "ylim"],
        "common": [
            "linestyle",
            "marker",
            "linewidth",
            "tick_size",
            "max_xticks",
            "markersize",
            "direct_line_labels",
        ],
    },
    "scatter": {
        "essential": ["color", "labels", "scale", "legend", "xlim", "ylim"],
        "common": ["marker", "markersize", "linewidth", "tick_size"],
    },
    "grouped_bar": {
        "essential": ["colors", "labels", "show_values", "value_format", "scale", "legend"],
        "common": ["width", "value_fontsize", "tick_size", "ylim"],
    },
    "bar": {
        "essential": ["colors", "show_values", "value_format", "scale", "legend"],
        "common": ["orientation", "negative_color", "sort_by", "tick_size", "ylim", "xlabel"],
    },
    "stacked_bar": {
        "essential": ["colors", "labels", "show_values", "value_format", "scale", "legend"],
        "common": ["stack_labels", "tick_size", "ylim"],
    },
    "lollipop": {
        "essential": [
            "colors",
            "sort_by",
            "sort_ascending",
            "end_marker_style",
            "end_marker_color",
        ],
        "common": [
            "marker_size",
            "y_axis_position",
            "hide_y_spine",
            "grid_axis",
            "start_value_labels",
            "end_value_labels",
            "range_labels",
            "category_wrap_length",
        ],
    },
    "donut": {
        "essential": ["colors", "show_percentages", "hole_size"],
        "common": ["center_text", "center_color", "label_distance"],
    },
    "waffle": {
        "essential": ["colors", "labels"],
        "common": ["vertical", "starting_location", "interval_ratio_x", "interval_ratio_y"],
    },
    "us_map_pie": {
        "essential": ["show_pie_labels", "show_percentages", "base_pie_size"],
        "common": ["show_state_boundaries", "legend"],
    },
}

# ---------------------------------------------------------------------------
# Per-chart-type quick-start guidance for the editor.
# ---------------------------------------------------------------------------

CHART_TYPE_GUIDANCE: dict[str, dict[str, Any]] = {
    "line": {
        "description": "Time-series and trend lines. Most common chart type for budget data.",
        "workflow": [
            "Bind x (usually fiscal year) and y (one or more value columns)",
            "Set colors and labels for each series",
            "Configure linestyle and marker if comparing series types",
            "Set scale (usually \u2018billions\u2019) and xlim for axis range",
            "Toggle legend on/off or use direct_line_labels",
        ],
        "tip": "For presidential comparisons, use dotted lines for requests and solid for appropriations.",
    },
    "scatter": {
        "description": "Scatter plots for comparing two variables.",
        "workflow": [
            "Bind x and y to numeric columns",
            "Set marker style and size",
            "Add colors and labels for series differentiation",
        ],
    },
    "grouped_bar": {
        "description": "Side-by-side bars for comparing categories across groups.",
        "workflow": [
            "Bind categories (x-axis labels) and groups (data series)",
            "Set colors for each group",
            "Enable show_values and set value_format for bar labels",
            "Configure legend position",
        ],
        "tip": "Use value_format: monetary with scale: billions for budget charts.",
    },
    "bar": {
        "description": "Simple bar charts for single-series comparisons.",
        "workflow": [
            "Bind categories and values",
            "Set colors (use negative_color for deficit highlighting)",
            "Enable show_values with appropriate value_format",
        ],
    },
    "stacked_bar": {
        "description": "Stacked bars for showing composition within categories.",
        "workflow": [
            "Bind categories and values (multiple series stack automatically)",
            "Set colors and labels for each stack segment",
            "Enable show_values and configure stack_labels for totals",
        ],
    },
    "lollipop": {
        "description": "Range charts showing start-to-end values per category.",
        "workflow": [
            "Bind categories, start_values, and end_values",
            "Configure sort_by and sort_ascending for ordering",
            "Set end_marker_style (e.g., \u2018X\u2019 for cancellations)",
            "Enable value labels for start/end annotations",
        ],
        "tip": "Use y_axis_position: right with hide_y_spine for clean label placement.",
    },
    "donut": {
        "description": "Proportional donut charts for showing composition.",
        "workflow": [
            "Bind labels and values",
            "Set colors and toggle show_percentages",
            "Configure hole_size, center_text, and center_color",
        ],
    },
    "waffle": {
        "description": "Waffle charts for part-of-whole visualisation.",
        "workflow": [
            "Bind values",
            "Set colors and labels",
            "Configure grid layout (vertical, starting_location)",
        ],
    },
    "us_map_pie": {
        "description": "Geographic pie charts overlaid on a U.S. state map.",
        "workflow": [
            "Bind state_data and pie_values from controller",
            "Configure base_pie_size and display options",
            "Toggle show_state_boundaries and show_pie_labels",
        ],
    },
}

# ---------------------------------------------------------------------------
# Series-correlated fields: when the trigger field is an array, these fields
# should be edited together per-series in a unified table editor.
# ---------------------------------------------------------------------------

_SERIES_CORRELATED: dict[str, dict[str, Any]] = {
    "line": {
        "trigger_field": "y",
        "correlated": [
            "color",
            "labels",
            "linestyle",
            "linewidth",
            "marker",
            "markersize",
            "alpha",
        ],
    },
    "scatter": {
        "trigger_field": "y",
        "correlated": [
            "color",
            "labels",
            "linestyle",
            "linewidth",
            "marker",
            "markersize",
            "alpha",
        ],
    },
}

# ---------------------------------------------------------------------------
# Composite widgets: groups of related array fields that should be edited as
# a single unified control instead of individual array fields.
# ---------------------------------------------------------------------------

_COMPOSITE_WIDGETS: dict[str, dict[str, dict[str, Any]]] = {
    "line": {
        "reference_lines": {
            "fields": [
                "hlines",
                "hline_labels",
                "hline_colors",
                "hline_styles",
                "hline_widths",
                "hline_alpha",
            ],
            "global_fields": [
                "hline_label_position",
                "hline_label_offset",
                "hline_label_fontsize",
                "hline_label_bbox",
            ],
        },
    },
    "scatter": {
        "reference_lines": {
            "fields": [
                "hlines",
                "hline_labels",
                "hline_colors",
                "hline_styles",
                "hline_widths",
                "hline_alpha",
            ],
            "global_fields": [
                "hline_label_position",
                "hline_label_offset",
                "hline_label_fontsize",
                "hline_label_bbox",
            ],
        },
    },
}


def get_chart_type_schema(chart_type: str) -> dict[str, Any]:
    """Return a cleaned JSON Schema for a single chart type.

    Uses ``CONFIG_REGISTRY[chart_type].model_json_schema()`` for a flat,
    per-type schema (NOT the full discriminated union).

    Post-processes the schema to strip null branches from anyOf while
    preserving multi-type union information for the custom form.
    """
    config_cls = CONFIG_REGISTRY.get(chart_type)
    if config_cls is None:
        raise ValueError(f"Unknown chart type: {chart_type}. Available: {list(CONFIG_REGISTRY)}")

    schema = config_cls.model_json_schema()
    schema = _strip_null_from_any_of(schema)

    # Strip excluded system fields from the schema
    excluded = _get_excluded_fields(config_cls)
    props = schema.get("properties", {})
    for field in excluded:
        props.pop(field, None)
    req = schema.get("required", [])
    if req:
        schema["required"] = [r for r in req if r not in excluded]

    return schema


def get_ui_schema(chart_type: str) -> dict[str, Any]:
    """Generate a uiSchema for the given chart type.

    The uiSchema controls RJSF rendering: field order, grouping,
    widget selection, help text, and inline row hints.
    """
    config_cls = CONFIG_REGISTRY.get(chart_type)
    if config_cls is None:
        raise ValueError(f"Unknown chart type: {chart_type}")

    excluded = _get_excluded_fields(config_cls)
    fields = [f for f in config_cls.model_fields if f not in excluded]
    field_infos = config_cls.model_fields

    ui: dict[str, Any] = {}

    # Build ordered field list and group assignments.
    # Use inheritance-aware grouping: a field only belongs to a mixin group
    # if the config class actually inherits from that mixin.  This prevents
    # generic names like ``alpha`` or ``linewidth`` from being labelled
    # "Bar Styling" on line/scatter/lollipop charts.
    groups: dict[str, list[str]] = {}
    for field_name in fields:
        group = _get_field_group(field_name, config_cls, chart_type)
        groups.setdefault(group, []).append(field_name)

    # Per-field uiSchema entries
    for field_name in fields:
        field_ui: dict[str, Any] = {}

        if field_name in _HIDDEN_FIELDS:
            field_ui["ui:widget"] = "hidden"

        if field_name in _COLOR_FIELDS:
            field_ui["ui:widget"] = "tpsColor"

        if field_name == "legend":
            field_ui["ui:widget"] = "legendBuilder"

        # Help text from field description
        info = field_infos.get(field_name)
        if info and info.description:
            field_ui["ui:help"] = info.description

        if field_ui:
            ui[field_name] = field_ui

    # Field ordering: identity first, then mixin groups, then chart-specific
    ordered_fields = []
    for group_name in GROUP_ORDER:
        if group_name in groups:
            ordered_fields.extend(groups[group_name])
    # Any remaining fields not in GROUP_ORDER
    for field_name in fields:
        if field_name not in ordered_fields:
            ordered_fields.append(field_name)

    ui["ui:order"] = ordered_fields

    # Group metadata for the ObjectFieldTemplate
    ui_groups = []
    for group_name in GROUP_ORDER:
        group_fields = groups.get(group_name, [])
        if group_fields:
            ui_groups.append(
                {
                    "name": group_name,
                    "fields": group_fields,
                    "defaultOpen": group_name == "Identity",
                }
            )
    ui["ui:groups"] = ui_groups

    # Inline row hints
    ui["ui:layout"] = {
        "rows": [list(pair) for pair in _INLINE_ROWS if all(f in field_infos for f in pair)]
    }

    return ui


_EDITOR_EXCLUDED_TYPES = {"line_subplots"}


def get_available_chart_types() -> list[str]:
    """Return sorted list of available chart type strings."""
    return sorted(k for k in CONFIG_REGISTRY if k not in _EDITOR_EXCLUDED_TYPES)


def get_primary_binding_fields(chart_type: str) -> list[str]:
    """Return chart-type-specific primary binding fields."""
    return list(PRIMARY_BINDING_FIELDS.get(chart_type, []))


def get_editor_hints(chart_type: str) -> dict[str, Any]:
    """Return editor-specific metadata for guided form rendering."""
    config_cls = CONFIG_REGISTRY.get(chart_type)
    if config_cls is None:
        raise ValueError(f"Unknown chart type: {chart_type}")

    excluded = _get_excluded_fields(config_cls)
    fields = [f for f in config_cls.model_fields if f not in excluded]
    primary = [f for f in get_primary_binding_fields(chart_type) if f in fields]
    annotation = [f for f in ("title", "subtitle", "source", "output") if f in fields]

    visual = [f for f in fields if f not in set(primary) | set(annotation) | {"type"}]
    advanced = [
        f
        for f in visual
        if _get_field_group(f, config_cls, chart_type) in {"Advanced", "Axis", "Grid"}
    ]
    suggested = [*primary, *[f for f in fields if f not in set(primary)]]

    # 3-tier field prioritisation
    tiers = FIELD_TIERS.get(chart_type, {})
    essential = [f for f in tiers.get("essential", []) if f in visual]
    common = [f for f in tiers.get("common", []) if f in visual]
    tier_promoted = set(essential) | set(common)
    advanced_from_tiers = [f for f in visual if f not in tier_promoted]

    hints: dict[str, Any] = {
        "primary_binding_fields": primary,
        "step_field_map": {
            "data_source_and_preparation": [
                "data.source",
                "data.params",
                "data.calculate_inflation",
            ],
            "data_bindings": primary,
            "visual_design": visual,
            "annotation_output": annotation,
        },
        "advanced_fields": advanced,
        "suggested_field_order": suggested,
        "field_tiers": {
            "essential": essential,
            "common": common,
            "advanced": advanced_from_tiers,
        },
    }

    # Series-correlated fields for multi-series editing
    if chart_type in _SERIES_CORRELATED:
        hints["series_correlated_fields"] = _SERIES_CORRELATED[chart_type]

    # Composite widgets (e.g. reference line builder)
    if chart_type in _COMPOSITE_WIDGETS:
        hints["composite_widgets"] = _COMPOSITE_WIDGETS[chart_type]

    # Quick-start guidance
    if chart_type in CHART_TYPE_GUIDANCE:
        hints["guidance"] = CHART_TYPE_GUIDANCE[chart_type]

    return hints


def get_data_source_schema() -> dict[str, Any]:
    """Return cleaned JSON schema for DataSourceConfig."""
    schema = DataSourceConfig.model_json_schema()
    return _strip_null_from_any_of(schema)


def get_data_ui_schema() -> dict[str, Any]:
    """Return uiSchema metadata for data source form rendering."""
    model_fields = DataSourceConfig.model_fields
    ui: dict[str, Any] = {}

    for field_name, info in model_fields.items():
        field_ui: dict[str, Any] = {}
        if info.description:
            field_ui["ui:help"] = info.description
        if field_ui:
            ui[field_name] = field_ui

    order = ["source", "params", "calculate_inflation"]
    ui["ui:order"] = [f for f in order if f in model_fields]
    ui["ui:groups"] = [
        {"name": "Data Source", "fields": ["source"], "defaultOpen": True},
        {"name": "Parameters", "fields": ["params"], "defaultOpen": True},
        {"name": "Inflation", "fields": ["calculate_inflation"], "defaultOpen": False},
    ]
    ui["ui:layout"] = {"rows": []}
    return ui


# ---------------------------------------------------------------------------
# Schema post-processing
# ---------------------------------------------------------------------------


def _strip_null_from_any_of(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip null branches from Pydantic's anyOf, preserving union types.

    Pydantic generates ``anyOf: [{type: X}, {type: null}]`` for Optional
    fields. This strips the null branch so the form sees only real types.
    Multi-type unions (e.g. ``bool | dict | str``) are preserved intact
    so the custom form can render the appropriate field per value type.

    For single non-null branches, collapses to a flat type.
    """
    if not isinstance(schema, dict):
        return schema

    cleaned = {**schema}

    if "anyOf" in cleaned:
        branches = cleaned["anyOf"]
        non_null = [b for b in branches if b.get("type") != "null"]

        if len(non_null) == 1:
            # Single type: collapse anyOf to flat schema
            best = non_null[0]
            result = {k: v for k, v in cleaned.items() if k != "anyOf"}
            result.update(best)
            cleaned = result
        elif len(non_null) > 1:
            # Multi-type union: keep anyOf with just the non-null branches
            cleaned["anyOf"] = non_null
        else:
            # Only null branches — treat as string
            result = {k: v for k, v in cleaned.items() if k != "anyOf"}
            result["type"] = "string"
            cleaned = result

    # Recurse into nested schemas
    for key in ("properties", "$defs"):
        if key in cleaned and isinstance(cleaned[key], dict):
            cleaned[key] = {
                k: _strip_null_from_any_of(v) if isinstance(v, dict) else v
                for k, v in cleaned[key].items()
            }

    for key in ("items", "additionalProperties"):
        if key in cleaned and isinstance(cleaned[key], dict):
            cleaned[key] = _strip_null_from_any_of(cleaned[key])

    return cleaned
