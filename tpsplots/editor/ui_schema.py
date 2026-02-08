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
# (export_data, matplotlib_config) that are not user-configurable in the
# editor. Stripping them from the JSON schema (not just hiding) prevents
# RJSF from creating form elements or injecting empty defaults.
_EXCLUDED_FIELDS = {"figsize", "dpi", "export_data", "matplotlib_config"}


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


def _get_field_group(field_name: str, config_cls: type) -> str:
    """Return the UI group for a field, checking mixin inheritance.

    A field is assigned to a mixin group only when *config_cls* actually
    inherits from that mixin.  Identity fields are always matched by name.
    Everything else falls through to "Chart-Specific".
    """
    if field_name in _IDENTITY_FIELDS:
        return "Identity"
    for group_name, mixin_cls in _MIXIN_GROUPS:
        if issubclass(config_cls, mixin_cls) and field_name in mixin_cls.model_fields:
            return group_name
    return "Chart-Specific"


# Ordered group names for the UI
GROUP_ORDER = [
    "Identity",
    "Data Bindings",
    "Bar Styling",
    "Value Labels",
    "Sort",
    "Scale",
    "Tick Format",
    "Legend",
    "Grid",
    "Axis",
    "Chart-Specific",
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
        group = _get_field_group(field_name, config_cls)
        groups.setdefault(group, []).append(field_name)

    # Per-field uiSchema entries
    for field_name in fields:
        field_ui: dict[str, Any] = {}

        if field_name in _HIDDEN_FIELDS:
            field_ui["ui:widget"] = "hidden"

        if field_name in _COLOR_FIELDS:
            field_ui["ui:widget"] = "tpsColor"

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
    # Chart-specific fields not in any known group
    remaining = [f for f in fields if f not in ordered_fields[: len(ordered_fields)]]
    if remaining:
        ui_groups.append(
            {
                "name": "Chart-Specific",
                "fields": remaining,
                "defaultOpen": False,
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
        f for f in visual if _get_field_group(f, config_cls) in {"Chart-Specific", "Axis", "Grid"}
    ]
    suggested = [*primary, *[f for f in fields if f not in set(primary)]]

    return {
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
    }


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
