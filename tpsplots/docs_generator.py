"""Auto-generate Markdown reference docs from Pydantic chart config models."""

from __future__ import annotations

import inspect
import types
import typing
from collections import OrderedDict
from dataclasses import dataclass
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

    # Chart type pages
    types_to_generate = chart_types or sorted(CONFIG_REGISTRY.keys())
    for chart_type in types_to_generate:
        config_cls = CONFIG_REGISTRY[chart_type]
        page = render_chart_page(chart_type, config_cls)
        page_path = output_dir / f"{chart_type}.md"
        page_path.write_text(page)
        written.append(page_path)

    return written
