"""Auto-generate Markdown reference docs from Pydantic chart config models."""

from __future__ import annotations

import inspect
import types
import typing
from collections import OrderedDict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from tpsplots.editor.ui_schema import (
    CHART_TYPE_GUIDANCE,
    GROUP_ORDER,
    _get_field_group,
)
from tpsplots.models.charts import CONFIG_REGISTRY
from tpsplots.models.data_sources import (
    CurrencyCleaningConfig,
    DataSourceConfig,
    DataSourceParams,
    InflationConfig,
)
from tpsplots.models.mixins.base import ChartConfigBase

# Fields excluded from per-chart docs (type is already the page heading)
_EXCLUDED_FIELDS = {"type"}

# Common fields that go in the "Common" group at the end of each chart page
_COMMON_FIELDS = set(ChartConfigBase.model_fields.keys()) - {"type"}

# Group name for common fields in chart pages
_COMMON_GROUP = "Common"


# ---------------------------------------------------------------------------
# Type description helpers
# ---------------------------------------------------------------------------


def _unwrap_annotated(annotation: Any) -> Any:
    """Strip Annotated wrappers, returning the inner type."""
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return typing.get_args(annotation)[0]
    return annotation


def describe_type(annotation: Any) -> str:
    """Convert a Python type annotation to a human-readable string for docs."""
    if annotation is type(None):
        return "null"

    if annotation is Any:
        return "any (template ref)"

    # Unwrap Annotated (e.g. BeforeValidator wrappers)
    raw = _unwrap_annotated(annotation)
    if raw is not annotation:
        return describe_type(raw)

    origin = typing.get_origin(raw)
    args = typing.get_args(raw)

    # Literal["a", "b"] → `"a"`, `"b"`
    if origin is typing.Literal:
        return ", ".join(f'`"{v}"`' for v in args)

    # Union types (X | Y | None)
    if origin is types.UnionType or origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        parts = [describe_type(a) for a in non_none]
        return " or ".join(parts)

    # list[X]
    if origin is list:
        if args:
            inner = describe_type(args[0])
            return f"list[{inner}]"
        return "list"

    # dict[K, V]
    if origin is dict:
        if args and len(args) == 2:
            k = describe_type(args[0])
            v = describe_type(args[1])
            return f"dict[{k}, {v}]"
        return "dict"

    # Pydantic sub-models
    if isinstance(raw, type) and issubclass(raw, BaseModel):
        return f"[{raw.__name__}](#{raw.__name__.lower()})"

    # Plain types
    if isinstance(raw, type):
        return raw.__name__

    return str(raw)


def format_default(field_info: FieldInfo) -> str:
    """Render a field's default value for display in docs."""
    if field_info.is_required():
        return "**required**"
    default = field_info.default
    if default is None:
        return "—"
    if isinstance(default, str):
        return f'`"{default}"`'
    if isinstance(default, bool):
        return f"`{str(default).lower()}`"
    if isinstance(default, (int, float)):
        return f"`{default}`"
    return f"`{default}`"


# ---------------------------------------------------------------------------
# Field grouping
# ---------------------------------------------------------------------------


@dataclass
class FieldRow:
    """A single field ready for rendering in a Markdown table."""

    name: str
    type_str: str
    default_str: str
    description: str


def get_grouped_fields(config_cls: type, chart_type: str) -> OrderedDict[str, list[FieldRow]]:
    """Group all fields for a chart config into ordered sections.

    Returns an OrderedDict mapping group name → list of FieldRow,
    ordered according to GROUP_ORDER with a "Common" group appended at the end.
    """
    groups: dict[str, list[FieldRow]] = {}

    for field_name, field_info in config_cls.model_fields.items():
        if field_name in _EXCLUDED_FIELDS:
            continue

        row = FieldRow(
            name=field_name,
            type_str=describe_type(field_info.annotation),
            default_str=format_default(field_info),
            description=field_info.description or "",
        )

        # Common fields go in a dedicated group at the end
        if field_name in _COMMON_FIELDS:
            groups.setdefault(_COMMON_GROUP, []).append(row)
        else:
            group = _get_field_group(field_name, config_cls, chart_type)
            groups.setdefault(group, []).append(row)

    # Order groups: GROUP_ORDER first, then any extras, then Common last
    ordered: OrderedDict[str, list[FieldRow]] = OrderedDict()
    for group_name in GROUP_ORDER:
        if group_name in groups and group_name != _COMMON_GROUP:
            ordered[group_name] = groups[group_name]
    # Any groups not in GROUP_ORDER (shouldn't happen, but defensive)
    for group_name in groups:
        if group_name not in ordered and group_name != _COMMON_GROUP:
            ordered[group_name] = groups[group_name]
    # Common always last
    if _COMMON_GROUP in groups:
        ordered[_COMMON_GROUP] = groups[_COMMON_GROUP]

    return ordered


# ---------------------------------------------------------------------------
# Sub-model discovery
# ---------------------------------------------------------------------------

# Known sub-models and which chart types use them
_SUB_MODELS: dict[str, tuple[type, list[str]]] = {}


def _discover_sub_models() -> dict[str, tuple[type, list[str]]]:
    """Find all Pydantic sub-models referenced by chart config fields."""
    if _SUB_MODELS:
        return _SUB_MODELS

    for chart_type, config_cls in CONFIG_REGISTRY.items():
        for _fname, finfo in config_cls.model_fields.items():
            for model_cls in _extract_sub_models(finfo.annotation):
                name = model_cls.__name__
                if name not in _SUB_MODELS:
                    _SUB_MODELS[name] = (model_cls, [])
                if chart_type not in _SUB_MODELS[name][1]:
                    _SUB_MODELS[name][1].append(chart_type)

    return _SUB_MODELS


def _extract_sub_models(annotation: Any) -> list[type]:
    """Recursively extract BaseModel subclasses from a type annotation."""
    results = []
    raw = _unwrap_annotated(annotation)
    args = typing.get_args(raw)

    if (
        isinstance(raw, type)
        and issubclass(raw, BaseModel)
        and raw.__module__.startswith("tpsplots")
        and raw not in CONFIG_REGISTRY.values()
        and not issubclass(raw, ChartConfigBase)
    ):
        results.append(raw)

    for arg in args:
        results.extend(_extract_sub_models(arg))

    return results


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_field_table(fields: list[FieldRow]) -> str:
    """Render a list of FieldRows as a Markdown table."""
    lines = [
        "| Field | Type | Default | Description |",
        "|-------|------|---------|-------------|",
    ]
    for f in fields:
        desc = f.description.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{f.name}` | {f.type_str} | {f.default_str} | {desc} |")
    return "\n".join(lines)


def render_sub_model(model_cls: type) -> str:
    """Render a sub-model's fields as a Markdown section."""
    lines = [f"### {model_cls.__name__}", ""]

    # First line of docstring
    doc = inspect.getdoc(model_cls)
    if doc:
        first_line = doc.split("\n")[0].strip()
        if first_line:
            lines.append(first_line)
            lines.append("")

    rows = []
    for field_name, field_info in model_cls.model_fields.items():
        rows.append(
            FieldRow(
                name=field_name,
                type_str=describe_type(field_info.annotation),
                default_str=format_default(field_info),
                description=field_info.description or "",
            )
        )

    lines.append(render_field_table(rows))
    return "\n".join(lines)


def render_model_section(model_cls: type, heading: str, level: int = 2) -> str:
    """Render any Pydantic model as a headed Markdown section."""
    prefix = "#" * level
    lines = [f"{prefix} {heading}", ""]

    doc = inspect.getdoc(model_cls)
    if doc:
        first_line = doc.split("\n")[0].strip()
        if first_line:
            lines.append(first_line)
            lines.append("")

    rows = []
    for field_name, field_info in model_cls.model_fields.items():
        rows.append(
            FieldRow(
                name=field_name,
                type_str=describe_type(field_info.annotation),
                default_str=format_default(field_info),
                description=field_info.description or "",
            )
        )

    lines.append(render_field_table(rows))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Minimal YAML examples per chart type
# ---------------------------------------------------------------------------

MINIMAL_EXAMPLES: dict[str, str] = {
    "line": """\
data:
  source: data/budget.csv

chart:
  type: line
  output: budget_trend
  title: "NASA Budget Over Time"
  x: "{{Fiscal Year}}"
  y: "{{Budget}}"\
""",
    "scatter": """\
data:
  source: data/missions.csv

chart:
  type: scatter
  output: cost_vs_mass
  title: "Mission Cost vs Mass"
  x: "{{Mass}}"
  y: "{{Cost}}"\
""",
    "bar": """\
data:
  source: data/directorates.csv

chart:
  type: bar
  output: directorate_budget
  title: "Budget by Directorate"
  categories: "{{Directorate}}"
  values: "{{Budget}}"\
""",
    "stacked_bar": """\
data:
  source: data/budget_breakdown.csv

chart:
  type: stacked_bar
  output: budget_stacked
  title: "Budget Breakdown by Year"
  categories: "{{Fiscal Year}}"
  values:
    "Science": "{{Science}}"
    "Exploration": "{{Exploration}}"\
""",
    "grouped_bar": """\
data:
  source: data/comparison.csv

chart:
  type: grouped_bar
  output: budget_comparison
  title: "Budget Comparison"
  categories: "{{Account}}"
  groups:
    - label: "FY 2024"
      values: "{{FY2024}}"
    - label: "FY 2025"
      values: "{{FY2025}}"\
""",
    "donut": """\
data:
  source: data/directorates.csv

chart:
  type: donut
  output: budget_donut
  title: "NASA Budget Composition"
  labels: "{{Directorate}}"
  values: "{{Budget}}"\
""",
    "lollipop": """\
data:
  source: data/missions.csv

chart:
  type: lollipop
  output: mission_timelines
  title: "Mission Duration"
  categories: "{{Mission}}"
  start_values: "{{Start Year}}"
  end_values: "{{End Year}}"\
""",
    "waffle": """\
data:
  source: data/composition.csv

chart:
  type: waffle
  output: budget_waffle
  title: "Budget Composition"
  values:
    "Science": "{{Science}}"
    "Exploration": "{{Exploration}}"\
""",
    "us_map_pie": """\
data:
  source: controller:your_controller.get_state_data

chart:
  type: us_map_pie
  output: state_distribution
  title: "Distribution by State"
  pie_data: "{{state_df}}"\
""",
    "line_subplots": """\
data:
  source: data/divisions.csv

chart:
  type: line_subplots
  output: science_divisions
  title: "Science Division Budgets"
  subplot_data:
    - x: "{{Fiscal Year}}"
      y: "{{Astrophysics}}"
      title: "Astrophysics"
      color: NeptuneBlue
    - x: "{{Fiscal Year}}"
      y: "{{Planetary}}"
      title: "Planetary Science"
      color: RocketFlame\
""",
}


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def render_chart_page(chart_type: str, config_cls: type) -> str:
    """Render a full self-contained Markdown page for a chart type."""
    lines: list[str] = []

    # Title
    display_name = chart_type.replace("_", " ").title()
    lines.append(f"# {display_name} Chart")
    lines.append("")
    lines.append("> Auto-generated from Pydantic models. Do not edit manually.")
    lines.append("> Regenerate with: `tpsplots docs`")
    lines.append("")
    lines.append("See also: [Data Configuration](data.md) | [All Chart Types](index.md)")
    lines.append("")

    # Description from guidance or docstring
    guidance = CHART_TYPE_GUIDANCE.get(chart_type, {})
    description = guidance.get("description", "")
    if not description:
        doc = inspect.getdoc(config_cls)
        if doc:
            description = doc.split("\n")[0].strip()
    if description:
        lines.append(description)
        lines.append("")

    # Minimal example
    example = MINIMAL_EXAMPLES.get(chart_type)
    if example:
        lines.append("## Example")
        lines.append("")
        lines.append("```yaml")
        lines.append(example)
        lines.append("```")
        lines.append("")

    # Grouped field tables
    grouped = get_grouped_fields(config_cls, chart_type)
    for group_name, fields in grouped.items():
        lines.append(f"## {group_name}")
        lines.append("")
        lines.append(render_field_table(fields))
        lines.append("")

    # Sub-models used by this chart type
    sub_models = _discover_sub_models()
    chart_sub_models = [
        (name, cls) for name, (cls, chart_types) in sub_models.items() if chart_type in chart_types
    ]
    if chart_sub_models:
        lines.append("## Sub-models")
        lines.append("")
        for _name, cls in chart_sub_models:
            lines.append(render_sub_model(cls))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_data_page() -> str:
    """Render the data configuration reference page."""
    lines = [
        "# Data Configuration",
        "",
        "> Auto-generated from Pydantic models. Do not edit manually.",
        "> Regenerate with: `tpsplots docs`",
        "",
        "See also: [All Chart Types](index.md)",
        "",
        "Fields under the `data:` key in YAML.",
        "",
        "## Example",
        "",
        "```yaml",
        "data:",
        "  source: https://docs.google.com/spreadsheets/d/.../export?format=csv",
        "  params:",
        "    columns:",
        '      - "Fiscal Year"',
        '      - "Budget"',
        "    cast:",
        "      Fiscal Year: int",
        "    auto_clean_currency: true",
        "  calculate_inflation:",
        "    columns:",
        '      - "Budget"',
        "    type: nnsi",
        "```",
        "",
    ]

    lines.append(render_model_section(DataSourceConfig, "DataSourceConfig"))
    lines.append("")
    lines.append(render_model_section(DataSourceParams, "DataSourceParams"))
    lines.append("")
    lines.append(render_model_section(InflationConfig, "InflationConfig"))
    lines.append("")
    lines.append(render_model_section(CurrencyCleaningConfig, "CurrencyCleaningConfig"))
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_index_page() -> str:
    """Render the index page listing all chart types."""
    lines = [
        "# TPS Plots — Chart Reference",
        "",
        "> Auto-generated from Pydantic models. Do not edit manually.",
        "> Regenerate with: `tpsplots docs`",
        "",
        "## Data Configuration",
        "",
        "- [Data Configuration](data.md) — source, params, inflation adjustment",
        "- [Controllers](controllers.md) — available data source methods for YAML",
        "",
        "## Chart Types",
        "",
    ]

    for chart_type in sorted(CONFIG_REGISTRY.keys()):
        display_name = chart_type.replace("_", " ").title()
        guidance = CHART_TYPE_GUIDANCE.get(chart_type, {})
        description = guidance.get("description", "")
        if description:
            lines.append(f"- [{display_name}]({chart_type}.md) — {description}")
        else:
            lines.append(f"- [{display_name}]({chart_type}.md)")

    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Controller discovery
# ---------------------------------------------------------------------------

# Base classes and abstract controllers to exclude from docs
_CONTROLLER_BASE_CLASSES = {"ChartController", "TabularDataController", "NASAFYChartsController"}

# Implicit controllers invoked via URL/CSV source strings, not controller: prefix
_IMPLICIT_CONTROLLERS = {"CSVController", "GoogleSheetsController"}

# Methods inherited from ChartController or object that are not data sources
_CONTROLLER_SKIP_METHODS = {
    "round_to_millions",
    "get_data_summary",
    "get_current_fy",
}


@dataclass
class ControllerMethod:
    """A public controller method ready for rendering."""

    name: str
    yaml_source: str
    description: str
    full_doc: str


@dataclass
class ControllerInfo:
    """A controller class with its public data-source methods."""

    class_name: str
    module_name: str
    description: str
    methods: list[ControllerMethod]


def discover_controllers() -> list[ControllerInfo]:
    """Discover all concrete controller classes and their public methods.

    Scans ``tpsplots.controllers`` for ChartController subclasses, filters
    out base classes and helper methods, and returns method metadata sorted
    by module name.

    Returns:
        List of ControllerInfo sorted by module_name.
    """
    import importlib
    import pkgutil

    import tpsplots.controllers
    from tpsplots.controllers.chart_controller import ChartController

    # Methods defined on ChartController itself (helpers, not data sources)
    base_methods = {
        name
        for name, _ in inspect.getmembers(ChartController, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    controllers: list[ControllerInfo] = []

    for _importer, modname, _ispkg in sorted(
        pkgutil.iter_modules(tpsplots.controllers.__path__),
        key=lambda x: x[1],
    ):
        try:
            mod = importlib.import_module(f"tpsplots.controllers.{modname}")
        except Exception:
            continue

        for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
            # Only concrete controllers defined in this module
            if not issubclass(cls, ChartController):
                continue
            if cls is ChartController:
                continue
            if cls_name in _CONTROLLER_BASE_CLASSES:
                continue
            if cls.__module__ != f"tpsplots.controllers.{modname}":
                continue

            # Collect public methods that aren't inherited from base
            methods: list[ControllerMethod] = []
            for method_name in sorted(dir(cls)):
                if method_name.startswith("_"):
                    continue
                if method_name in base_methods:
                    continue
                if method_name in _CONTROLLER_SKIP_METHODS:
                    continue

                attr = getattr(cls, method_name, None)
                if attr is None or not callable(attr):
                    continue
                # Skip class-level properties/cached_property
                if isinstance(
                    inspect.getattr_static(cls, method_name), (property, cached_property)
                ):
                    continue

                doc = inspect.getdoc(attr) or ""
                first_line = doc.split("\n")[0].strip() if doc else ""

                methods.append(
                    ControllerMethod(
                        name=method_name,
                        yaml_source=f"{modname}.{method_name}",
                        description=first_line,
                        full_doc=doc,
                    )
                )

            if not methods:
                continue

            # Use __doc__ directly to avoid inheriting ChartController's docstring
            cls_doc = cls.__doc__ or ""
            cls_desc = cls_doc.strip().split("\n")[0].strip() if cls_doc.strip() else ""

            controllers.append(
                ControllerInfo(
                    class_name=cls_name,
                    module_name=modname,
                    description=cls_desc,
                    methods=methods,
                )
            )

    return controllers


def _render_implicit_controllers(lines: list[str]) -> None:
    """Render the CSV and Google Sheets section for implicit data sources."""
    lines.extend(
        [
            "## CSV and Google Sheets",
            "",
            "CSV files and Google Sheets URLs are loaded automatically when used",
            "as the `data.source` value — no controller prefix is needed.",
            "",
            "```yaml",
            "# Local CSV file",
            "data:",
            "  source: data/budget.csv",
            "",
            "# Google Sheets (public, exported as CSV)",
            "data:",
            "  source: https://docs.google.com/spreadsheets/d/.../export?format=csv",
            "```",
            "",
            "Both produce a result dict containing:",
            "",
            "- One key per column in the dataset, mapped to its Series",
            "  (e.g. `{{Fiscal Year}}`, `{{Budget}}`)",
            "- `data` — the full DataFrame",
            "- `export_df` — DataFrame for CSV export",
            "- `metadata` — standard metadata (see below)",
            "",
            "Use `data.params` to customize loading. "
            "See [Data Configuration](data.md) for the full params reference.",
            "",
        ]
    )


def _render_metadata_section(lines: list[str]) -> None:
    """Render the standard metadata keys section."""
    lines.extend(
        [
            "## Standard Metadata",
            "",
            "Every controller returns a `metadata` dict with context values",
            "available for `{{...}}` template references in `title`, `subtitle`,",
            "and `source` fields. The standard keys are:",
            "",
            "| Key | Type | Description |",
            "|-----|------|-------------|",
            "| `max_fiscal_year` | int | Latest fiscal year in the dataset |",
            "| `min_fiscal_year` | int | Earliest fiscal year in the dataset |",
            "| `inflation_adjusted_year` | int | Target year for inflation adjustment (when applicable) |",
            "| `source` | str | Source attribution string |",
            "| `column_sums` | dict | Column totals (when ColumnSumProcessor runs) |",
            "",
            "CSV and Google Sheets controllers auto-produce per-column keys for"
            " numeric columns, and custom controllers can opt in explicitly by"
            " passing `value_columns` to `_build_metadata`:",
            "",
            "| Key pattern | Description |",
            "|-------------|-------------|",
            "| `max_{name}_fiscal_year` | Latest FY with non-null data for that column |",
            "| `min_{name}_fiscal_year` | Earliest FY with non-null data for that column |",
            "| `max_{name}` | Maximum value for that column |",
            "| `min_{name}` | Minimum value for that column |",
            "",
            "Individual controllers may add extra keys (e.g. `total_budget`,"
            " `total_projects`). See each method's Returns section below.",
            "",
        ]
    )


def render_controllers_index() -> str:
    """Render the controllers index page with links to individual controller docs."""
    lines = [
        "# Controllers",
        "",
        "> Auto-generated from controller docstrings. Do not edit manually.",
        "> Regenerate with: `tpsplots docs`",
        "",
        "See also: [Data Configuration](data.md) | [All Chart Types](index.md)",
        "",
        "Controllers provide data to charts via the `data.source` field in YAML:",
        "",
        "```yaml",
        "data:",
        "  source: nasa_budget_chart.nasa_budget_by_year",
        "```",
        "",
    ]

    all_controllers = discover_controllers()
    explicit = [c for c in all_controllers if c.class_name not in _IMPLICIT_CONTROLLERS]

    # Implicit controllers section
    _render_implicit_controllers(lines)

    # Standard metadata section
    _render_metadata_section(lines)

    # Links to individual controller pages
    lines.append("## Controllers")
    lines.append("")
    for ctrl in explicit:
        desc = f" — {ctrl.description}" if ctrl.description else ""
        lines.append(f"- [`{ctrl.module_name}`](controllers/{ctrl.module_name}.md){desc}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_controller_page(ctrl: ControllerInfo) -> str:
    """Render a single controller's reference page."""
    lines = [
        f"# {ctrl.module_name}",
        "",
        "> Auto-generated from controller docstrings. Do not edit manually.",
        "> Regenerate with: `tpsplots docs`",
        "",
        "See also: [All Controllers](../controllers.md) | [Data Configuration](../data.md)",
        "",
        f"**Class:** `{ctrl.class_name}`",
        "",
    ]

    if ctrl.description:
        lines.append(ctrl.description)
        lines.append("")

    lines.append("| Method | YAML Source | Description |")
    lines.append("|--------|------------|-------------|")
    for m in ctrl.methods:
        desc = m.description.replace("|", "\\|")
        lines.append(f"| `{m.name}()` | `{m.yaml_source}` | {desc} |")
    lines.append("")

    # Detailed method docs
    for m in ctrl.methods:
        lines.append(f"## `{m.yaml_source}`")
        lines.append("")
        if m.full_doc:
            lines.append(m.full_doc)
        else:
            lines.append("*No documentation available.*")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Top-level generation
# ---------------------------------------------------------------------------


def generate_all(output_dir: Path, chart_types: list[str] | None = None) -> list[Path]:
    """Generate all documentation files into output_dir.

    Args:
        output_dir: Directory to write files into (created if needed).
        chart_types: If specified, only generate these chart types.
            Index and data pages are always generated.

    Returns:
        List of paths written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Index
    index_path = output_dir / "index.md"
    index_path.write_text(render_index_page())
    written.append(index_path)

    # Data page
    data_path = output_dir / "data.md"
    data_path.write_text(render_data_page())
    written.append(data_path)

    # Controllers index + per-controller pages
    controllers_path = output_dir / "controllers.md"
    controllers_path.write_text(render_controllers_index())
    written.append(controllers_path)

    all_controllers = discover_controllers()
    explicit = [c for c in all_controllers if c.class_name not in _IMPLICIT_CONTROLLERS]
    if explicit:
        ctrl_dir = output_dir / "controllers"
        ctrl_dir.mkdir(parents=True, exist_ok=True)
        for ctrl in explicit:
            ctrl_path = ctrl_dir / f"{ctrl.module_name}.md"
            ctrl_path.write_text(render_controller_page(ctrl))
            written.append(ctrl_path)

    # Chart type pages
    types_to_generate = chart_types or sorted(CONFIG_REGISTRY.keys())
    for chart_type in types_to_generate:
        config_cls = CONFIG_REGISTRY[chart_type]
        page = render_chart_page(chart_type, config_cls)
        page_path = output_dir / f"{chart_type}.md"
        page_path.write_text(page)
        written.append(page_path)

    return written
