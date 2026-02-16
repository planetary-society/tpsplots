"""Config/View sync test — ensures Pydantic config models stay in sync with view code.

WHY THIS TEST EXISTS
====================
TPS Plots uses a two-layer architecture for chart parameters:

  1. **Config models** (tpsplots/models/charts/*.py) — Pydantic models that validate
     YAML input. Each chart type has a config model declaring every accepted field
     with types, defaults, and descriptions. These models drive the JSON schema
     that powers API docs, form builders, and YAML validation.

  2. **View classes** (tpsplots/views/*.py) — Matplotlib rendering code that
     consumes parameters via ``kwargs.pop("field_name", default)``. Each view's
     ``_create_chart()`` and ``_apply_*_styling()`` methods extract the parameters
     they need from a kwargs dict.

The risk is **drift**: a developer adds ``kwargs.pop("new_param")`` in a view
without adding the field to the config model (or vice versa). When this happens:
  - YAML users get no validation or autocompletion for the new parameter
  - The JSON schema becomes incomplete
  - ``extra="forbid"`` on the config means YAML with the undeclared key is rejected

HOW THIS TEST WORKS
===================
Rather than coupling config models to view code at runtime (which would require
passing config objects through the entire rendering pipeline and refactoring 232
kwargs.pop() calls), this test uses **static analysis** via Python's ``ast`` module:

  1. For each view class in VIEW_REGISTRY, get its CONFIG_CLASS
  2. Parse the view module's source code into an AST
  3. Walk the AST to find every ``kwargs.pop("key_name", ...)`` call
  4. Assert each key exists as a field on the config model

This approach:
  - Catches drift at CI time with a clear error message
  - Requires zero changes to the runtime call chain
  - Works statically (no matplotlib imports, no figure creation, fast)
  - Finds keys in all code paths, including error branches and styling helpers

INTERNAL KEYS ALLOWLIST
=======================
Some kwargs are NOT user-facing config fields — they're injected by the framework
or passed between internal methods. These are listed in INTERNAL_KEYS and excluded
from the sync check. If this set grows large, it's a signal that the config models
are incomplete.

WHAT TO DO WHEN THIS TEST FAILS
================================
If you see: "BarChartView pops kwargs not on BarChartConfig: {'new_param'}"

  1. Add ``new_param`` as a field to the appropriate config model in
     tpsplots/models/charts/<chart_type>.py (or a mixin if shared)
  2. If the param is internal/framework-only (not user-facing), add it to
     INTERNAL_KEYS with a comment explaining why
"""

import ast
import inspect

from tpsplots.views import VIEW_REGISTRY

# Keys that are internal to the framework — not user-facing config fields.
# These are injected by generate_chart(), _setup_figure(), or passed between
# internal methods within _create_chart(). Keep this set small; if it grows,
# the config models likely need updating instead.
INTERNAL_KEYS = {
    # Injected by ChartView.generate_chart() / create_figure() before calling _create_chart()
    "style",
    # Computed by LineChartView._create_chart() and passed to _apply_axes_styling()
    # as internal state — not settable by YAML users
    "x_data",
    "y_data",
    "line_colors",
    "line_labels",
    # Dual y-axis: computed state for right-axis rendering
    "y_right_data",
    "ax2",
    "right_colors",
    "right_labels",
}


def _extract_kwargs_pop_keys(source: str) -> set[str]:
    """Extract all string literal keys from ``kwargs.pop("key", ...)`` calls.

    Uses Python's ast module to parse source code statically — this catches
    kwargs.pop() calls in ALL code paths, including conditional branches,
    error handlers, and helper methods that wouldn't be exercised by a
    normal test run.

    Only matches the pattern: ``<name>.pop(<string_literal>, ...)``.
    Does not match dict literals, getattr calls, or variable keys.
    """
    tree = ast.parse(source)
    keys = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "kwargs"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            keys.add(node.args[0].value)
    return keys


def test_view_kwargs_match_config_fields():
    """Every kwargs.pop() key in a view module must exist on its config model.

    Iterates over all registered chart views, parses their source, and
    checks that every kwarg they consume is declared as a field on the
    corresponding Pydantic config model. This prevents config/view drift.
    """
    for _method_name, view_class in VIEW_REGISTRY.items():
        config_class = view_class.CONFIG_CLASS
        assert config_class is not None, (
            f"{view_class.__name__} is missing CONFIG_CLASS — add a class variable "
            f"pointing to its Pydantic config model"
        )

        # Collect all field names from the config model (includes inherited mixin fields)
        config_fields = set(config_class.model_fields.keys())

        # Parse the entire view module source to catch kwargs consumed by
        # _create_chart, _apply_*_styling, and any other helper methods
        module = inspect.getmodule(view_class)
        source = inspect.getsource(module)
        popped_keys = _extract_kwargs_pop_keys(source) - INTERNAL_KEYS

        missing = popped_keys - config_fields
        assert not missing, (
            f"{view_class.__name__} pops kwargs not declared on "
            f"{config_class.__name__}: {sorted(missing)}\n"
            f"  -> Add these as fields to the config model, or if they are "
            f"internal/framework-only, add them to INTERNAL_KEYS in this test."
        )
