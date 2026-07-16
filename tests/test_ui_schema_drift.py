"""Drift guards for the hand-maintained field tables in ``ui_schema.py``.

The editor's guided-form behaviour is driven by several hand-written lookup
tables that reference Pydantic *field names* by string. When a chart config
model is refactored (a field renamed or removed) these tables silently drift:
the stale entry is quietly filtered out downstream, so nothing errors but the
field disappears from the intended editor group/tier. These tests assert every
field name referenced in those tables still exists on the corresponding config
model, so the drift surfaces as a test failure instead of a silent UX gap.

``CHART_TYPE_GUIDANCE`` is intentionally excluded: it is human-facing prose,
not a field-name table.
"""

from __future__ import annotations

import pytest

from tpsplots.editor import ui_schema
from tpsplots.models.charts import CONFIG_REGISTRY


def _model_fields(chart_type: str) -> set[str]:
    """Field names declared on the config model for *chart_type*."""
    assert chart_type in CONFIG_REGISTRY, f"unknown chart type: {chart_type}"
    return set(CONFIG_REGISTRY[chart_type].model_fields)


def _all_model_fields() -> set[str]:
    """Union of field names across every registered config model."""
    fields: set[str] = set()
    for config_cls in CONFIG_REGISTRY.values():
        fields |= set(config_cls.model_fields)
    return fields


# ---------------------------------------------------------------------------
# Per-chart-type tables: keys are chart types, values reference that type's
# own model fields.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chart_type", sorted(ui_schema._CHART_FIELD_GROUPS))
def test_chart_field_groups_reference_real_fields(chart_type: str) -> None:
    """Every field in ``_CHART_FIELD_GROUPS`` exists on its config model."""
    model_fields = _model_fields(chart_type)
    missing = [f for f in ui_schema._CHART_FIELD_GROUPS[chart_type] if f not in model_fields]
    assert not missing, f"_CHART_FIELD_GROUPS[{chart_type!r}] references unknown fields: {missing}"


@pytest.mark.parametrize("chart_type", sorted(ui_schema.FIELD_TIERS))
def test_field_tiers_reference_real_fields(chart_type: str) -> None:
    """Every field in ``FIELD_TIERS`` (all tiers) exists on its config model."""
    model_fields = _model_fields(chart_type)
    missing = [
        f
        for tier_fields in ui_schema.FIELD_TIERS[chart_type].values()
        for f in tier_fields
        if f not in model_fields
    ]
    assert not missing, f"FIELD_TIERS[{chart_type!r}] references unknown fields: {missing}"


@pytest.mark.parametrize("chart_type", sorted(ui_schema.PRIMARY_BINDING_FIELDS))
def test_primary_binding_fields_reference_real_fields(chart_type: str) -> None:
    """Every field in ``PRIMARY_BINDING_FIELDS`` exists on its config model."""
    model_fields = _model_fields(chart_type)
    missing = [f for f in ui_schema.PRIMARY_BINDING_FIELDS[chart_type] if f not in model_fields]
    assert not missing, (
        f"PRIMARY_BINDING_FIELDS[{chart_type!r}] references unknown fields: {missing}"
    )


@pytest.mark.parametrize("chart_type", sorted(ui_schema._SERIES_CORRELATED))
def test_series_correlated_reference_real_fields(chart_type: str) -> None:
    """Trigger and correlated fields in ``_SERIES_CORRELATED`` exist on the model."""
    model_fields = _model_fields(chart_type)
    entry = ui_schema._SERIES_CORRELATED[chart_type]

    referenced: list[str] = []
    for key in ("trigger_field", "secondary_trigger_field"):
        value = entry.get(key)
        if value:
            referenced.append(value)
    referenced.extend(entry.get("correlated", []))

    missing = [f for f in referenced if f not in model_fields]
    assert not missing, f"_SERIES_CORRELATED[{chart_type!r}] references unknown fields: {missing}"


@pytest.mark.parametrize("chart_type", sorted(ui_schema._COMPOSITE_WIDGETS))
def test_composite_widgets_reference_real_fields(chart_type: str) -> None:
    """Every field/global_field in ``_COMPOSITE_WIDGETS`` exists on the model."""
    model_fields = _model_fields(chart_type)

    referenced: list[str] = []
    for widget in ui_schema._COMPOSITE_WIDGETS[chart_type].values():
        referenced.extend(widget.get("fields", []))
        referenced.extend(widget.get("global_fields", []))

    missing = [f for f in referenced if f not in model_fields]
    assert not missing, f"_COMPOSITE_WIDGETS[{chart_type!r}] references unknown fields: {missing}"


# ---------------------------------------------------------------------------
# Non-per-type tables: a flat set validated against the union of all models.
# ---------------------------------------------------------------------------


def test_color_fields_reference_real_fields() -> None:
    """Every name in ``_COLOR_FIELDS`` exists on at least one config model."""
    all_fields = _all_model_fields()
    missing = [f for f in ui_schema._COLOR_FIELDS if f not in all_fields]
    assert not missing, f"_COLOR_FIELDS references fields on no config model: {missing}"


@pytest.mark.parametrize("chart_type", sorted(ui_schema._CHART_EXCLUDED_FIELDS))
def test_chart_excluded_fields_reference_real_fields(chart_type: str) -> None:
    """Every field in ``_CHART_EXCLUDED_FIELDS`` exists on its config model.

    A renamed excluded field would silently stop being suppressed and
    reappear in the editor.
    """
    model_fields = _model_fields(chart_type)
    missing = [f for f in ui_schema._CHART_EXCLUDED_FIELDS[chart_type] if f not in model_fields]
    assert not missing, (
        f"_CHART_EXCLUDED_FIELDS[{chart_type!r}] references unknown fields: {missing}"
    )


def test_inline_rows_reference_real_fields() -> None:
    """Every field in ``_INLINE_ROWS`` pairs exists on at least one config model."""
    all_fields = _all_model_fields()
    missing = [f for pair in ui_schema._INLINE_ROWS for f in pair if f not in all_fields]
    assert not missing, f"_INLINE_ROWS references unknown fields: {missing}"


def test_optional_binding_fields_reference_real_fields() -> None:
    """Every field in ``OPTIONAL_BINDING_FIELDS`` exists on at least one config model."""
    all_fields = _all_model_fields()
    missing = [f for f in ui_schema.OPTIONAL_BINDING_FIELDS if f not in all_fields]
    assert not missing, f"OPTIONAL_BINDING_FIELDS references unknown fields: {missing}"
