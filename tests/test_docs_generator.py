"""Tests for auto-generated chart reference documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pytest
from pydantic import BaseModel

from tpsplots.docs_generator import (
    MINIMAL_EXAMPLES,
    FieldRow,
    describe_type,
    format_default,
    generate_all,
    get_grouped_fields,
    render_chart_page,
    render_data_page,
    render_field_table,
    render_index_page,
)
from tpsplots.models.charts import CONFIG_REGISTRY
from tpsplots.models.data_sources import DataSourceConfig

# ---------------------------------------------------------------------------
# describe_type
# ---------------------------------------------------------------------------


class _FakeSubModel(BaseModel):
    x: int = 0


@pytest.mark.parametrize(
    "annotation, expected",
    [
        (str, "str"),
        (int, "int"),
        (float, "float"),
        (bool, "bool"),
        (Any, "any (template ref)"),
        (type(None), "null"),
        # Literal
        (Literal["a", "b"], '`"a"`, `"b"`'),
        # Union with None
        (str | None, "str"),
        (str | list[str] | None, "str or list[str]"),
        # list
        (list[str], "list[str]"),
        (list[int], "list[int]"),
        # dict
        (dict[str, Any], "dict[str, any (template ref)]"),
        # Sub-model renders as Markdown link
        (_FakeSubModel, "[_FakeSubModel](#_fakesubmodel)"),
    ],
)
def test_describe_type(annotation, expected):
    result = describe_type(annotation)
    assert result == expected


def test_describe_type_literal_single():
    assert describe_type(Literal["vertical"]) == '`"vertical"`'


# ---------------------------------------------------------------------------
# format_default
# ---------------------------------------------------------------------------


def test_format_default_required():
    class M(BaseModel):
        x: str

    assert format_default(M.model_fields["x"]) == "**required**"


def test_format_default_none():
    class M(BaseModel):
        x: str | None = None

    assert format_default(M.model_fields["x"]) == "—"


def test_format_default_string():
    class M(BaseModel):
        x: str = "auto"

    assert format_default(M.model_fields["x"]) == '`"auto"`'


def test_format_default_bool():
    class M(BaseModel):
        x: bool = True

    assert format_default(M.model_fields["x"]) == "`true`"


def test_format_default_number():
    class M(BaseModel):
        x: float = 0.7

    assert format_default(M.model_fields["x"]) == "`0.7`"


# ---------------------------------------------------------------------------
# render_field_table
# ---------------------------------------------------------------------------


def test_render_field_table():
    rows = [
        FieldRow(name="x", type_str="str", default_str="—", description="X value"),
        FieldRow(name="y", type_str="int", default_str="**required**", description="Y value"),
    ]
    table = render_field_table(rows)
    assert "| `x` | str | — | X value |" in table
    assert "| `y` | int | **required** | Y value |" in table
    assert table.startswith("| Field |")


# ---------------------------------------------------------------------------
# get_grouped_fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_grouped_fields_covers_all_fields(chart_type):
    """Every model field (except 'type') appears in exactly one group."""
    config_cls = CONFIG_REGISTRY[chart_type]
    grouped = get_grouped_fields(config_cls, chart_type)

    all_field_names = {row.name for rows in grouped.values() for row in rows}
    expected = set(config_cls.model_fields.keys()) - {"type"}
    assert all_field_names == expected, (
        f"Missing: {expected - all_field_names}, Extra: {all_field_names - expected}"
    )


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_common_group_present(chart_type):
    """Every chart type has a 'Common' group with the ChartConfigBase fields."""
    config_cls = CONFIG_REGISTRY[chart_type]
    grouped = get_grouped_fields(config_cls, chart_type)
    assert "Common" in grouped
    common_names = {row.name for row in grouped["Common"]}
    # At minimum: output, title
    assert "output" in common_names
    assert "title" in common_names


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_common_group_is_last(chart_type):
    """The 'Common' group is always the last group."""
    config_cls = CONFIG_REGISTRY[chart_type]
    grouped = get_grouped_fields(config_cls, chart_type)
    group_names = list(grouped.keys())
    assert group_names[-1] == "Common"


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_chart_page_renders(chart_type):
    """Every chart type renders a non-empty page without errors."""
    config_cls = CONFIG_REGISTRY[chart_type]
    page = render_chart_page(chart_type, config_cls)
    assert len(page) > 100
    assert f"# {chart_type.replace('_', ' ').title()} Chart" in page


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_chart_page_has_example(chart_type):
    """Every chart type page includes a YAML example."""
    config_cls = CONFIG_REGISTRY[chart_type]
    page = render_chart_page(chart_type, config_cls)
    assert "```yaml" in page
    assert f"type: {chart_type}" in page


def test_data_page_renders():
    """Data page renders with all DataSourceConfig fields."""
    page = render_data_page()
    assert "# Data Configuration" in page
    for field_name in DataSourceConfig.model_fields:
        assert f"`{field_name}`" in page


def test_index_page_renders():
    """Index page lists all chart types."""
    page = render_index_page()
    assert "# TPS Plots" in page
    for chart_type in CONFIG_REGISTRY:
        assert f"{chart_type}.md" in page


@pytest.mark.parametrize("chart_type", sorted(CONFIG_REGISTRY.keys()))
def test_chart_page_contains_common_fields(chart_type):
    """Every chart page includes the common ChartConfigBase fields inline."""
    config_cls = CONFIG_REGISTRY[chart_type]
    page = render_chart_page(chart_type, config_cls)
    assert "## Common" in page
    assert "`output`" in page
    assert "`title`" in page
    assert "`subtitle`" in page


# ---------------------------------------------------------------------------
# Minimal examples
# ---------------------------------------------------------------------------


def test_minimal_examples_cover_all_types():
    """Every chart type in CONFIG_REGISTRY has a minimal example."""
    for chart_type in CONFIG_REGISTRY:
        assert chart_type in MINIMAL_EXAMPLES, f"Missing MINIMAL_EXAMPLES['{chart_type}']"


# ---------------------------------------------------------------------------
# generate_all
# ---------------------------------------------------------------------------


def test_generate_all(tmp_path):
    """generate_all creates all expected files."""
    written = generate_all(tmp_path)

    # Top-level files
    top_level_names = {p.name for p in written if p.parent == tmp_path}
    expected_top = {"index.md", "data.md", "controllers.md"} | {
        f"{ct}.md" for ct in CONFIG_REGISTRY
    }
    assert top_level_names == expected_top

    # Controller subdirectory files exist
    ctrl_files = [p for p in written if p.parent.name == "controllers"]
    assert len(ctrl_files) > 0, "No controller files generated in controllers/"
    assert (tmp_path / "controllers" / "apollo_controller.md").exists()

    # All files are non-empty
    for path in written:
        content = path.read_text()
        assert len(content) > 50, f"{path.name} is too short"


def test_generate_single_type(tmp_path):
    """generate_all with chart_types filter creates only the specified type."""
    written = generate_all(tmp_path, chart_types=["bar"])

    names = {p.name for p in written}
    assert "bar.md" in names
    assert "index.md" in names
    assert "data.md" in names
    # Other chart types should not be present
    assert "line.md" not in names


# ---------------------------------------------------------------------------
# Controller docs
# ---------------------------------------------------------------------------


def test_discover_controllers():
    """discover_controllers returns concrete controllers with methods."""
    from tpsplots.docs_generator import discover_controllers

    controllers = discover_controllers()
    assert len(controllers) > 0

    # Every controller has at least one method
    for ctrl in controllers:
        assert len(ctrl.methods) > 0, f"{ctrl.class_name} has no methods"

    # Known controllers are present
    module_names = {c.module_name for c in controllers}
    assert "apollo_controller" in module_names
    assert "nasa_budget_chart" in module_names
    assert "planetary_mission_budget" in module_names


def test_discover_controllers_excludes_base_classes():
    """Base classes should not appear in discovered controllers."""
    from tpsplots.docs_generator import discover_controllers

    controllers = discover_controllers()
    class_names = {c.class_name for c in controllers}
    assert "ChartController" not in class_names
    assert "TabularDataController" not in class_names
    assert "NASAFYChartsController" not in class_names


def test_all_controller_methods_have_docstrings():
    """Every public controller method should have a non-empty docstring."""
    from tpsplots.docs_generator import discover_controllers

    controllers = discover_controllers()
    missing = []
    for ctrl in controllers:
        for m in ctrl.methods:
            if not m.description:
                missing.append(m.yaml_source)
    assert not missing, f"Methods missing docstrings: {missing}"


def test_controllers_index_renders():
    """Controllers index page links to individual controller pages."""
    from tpsplots.docs_generator import render_controllers_index

    page = render_controllers_index()
    assert "# Controllers" in page
    assert "## CSV and Google Sheets" in page
    assert "## Standard Metadata" in page
    # Links to individual controller pages
    assert "controllers/apollo_controller.md" in page
    assert "controllers/nasa_budget_chart.md" in page


def test_controller_page_renders():
    """Individual controller page renders with methods."""
    from tpsplots.docs_generator import discover_controllers, render_controller_page

    controllers = discover_controllers()
    apollo = next(c for c in controllers if c.module_name == "apollo_controller")
    page = render_controller_page(apollo)
    assert "# apollo_controller" in page
    assert "program_spending" in page
    assert "YAML Source" in page


def test_index_includes_controllers():
    """Index page links to controllers page."""
    page = render_index_page()
    assert "controllers.md" in page


# ---------------------------------------------------------------------------
# Snapshot: docs stay in sync with models
# ---------------------------------------------------------------------------

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


@pytest.mark.skipif(not DOCS_DIR.exists(), reason="docs/ not yet generated")
def test_docs_up_to_date(tmp_path):
    """Committed docs match freshly generated output."""
    generate_all(tmp_path)

    # Check top-level docs
    for committed_file in DOCS_DIR.glob("*.md"):
        fresh = tmp_path / committed_file.name
        if not fresh.exists():
            continue
        committed_content = committed_file.read_text()
        fresh_content = fresh.read_text()
        assert committed_content == fresh_content, (
            f"{committed_file.name} is out of date. Run 'tpsplots docs' to regenerate."
        )

    # Check controllers subdirectory
    ctrl_dir = DOCS_DIR / "controllers"
    if ctrl_dir.exists():
        for committed_file in ctrl_dir.glob("*.md"):
            fresh = tmp_path / "controllers" / committed_file.name
            if not fresh.exists():
                continue
            committed_content = committed_file.read_text()
            fresh_content = fresh.read_text()
            assert committed_content == fresh_content, (
                f"controllers/{committed_file.name} is out of date. "
                "Run 'tpsplots docs' to regenerate."
            )
