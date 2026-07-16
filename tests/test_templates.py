"""Tests for the CLI scaffold templates (``tpsplots --new <type>``).

These guard against templates drifting away from the config models they are
meant to scaffold. Template values may contain ``{{...}}`` references that do
not resolve at load time, so we validate field *names* against the model's
``model_fields`` rather than running full Pydantic validation.
"""

import re

import pytest
import yaml

from tpsplots.models.charts import CONFIG_REGISTRY
from tpsplots.schema import get_chart_types
from tpsplots.templates import TEMPLATES, get_template

CHART_TYPES = get_chart_types()

# A commented-out chart option at top level: two-space indent, "# key:".
# Deeper-indented comments (nested sub-model fields, numbered prose) and
# section headers ("# === ... ===") deliberately don't match.
COMMENTED_CHART_FIELD = re.compile(r"^  # ([a-z_][a-z0-9_]*):", re.MULTILINE)


def _chart_section(template: str) -> str:
    """Return the template text from the ``chart:`` line onward."""
    return template.split("\nchart:\n", 1)[1]


def test_every_chart_type_has_a_template():
    """Every chart type the CLI advertises must have a scaffold template."""
    missing = [chart_type for chart_type in CHART_TYPES if chart_type not in TEMPLATES]
    assert not missing, f"Chart types without a template: {missing}"


@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_template_chart_section_parses(chart_type):
    """Each template must be valid YAML with a ``chart`` mapping."""
    template = get_template(chart_type)
    parsed = yaml.safe_load(template)

    assert isinstance(parsed, dict), f"{chart_type} template did not parse to a mapping"
    assert "chart" in parsed, f"{chart_type} template has no 'chart' section"
    assert isinstance(parsed["chart"], dict), f"{chart_type} 'chart' section is not a mapping"
    assert parsed["chart"].get("type") == chart_type


@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_template_chart_fields_exist_on_config_model(chart_type):
    """Every ``chart:`` field a template mentions must exist on the config model.

    Covers both the uncommented fields (via ``yaml.safe_load``) and the
    commented-out option lines (via a top-level ``# key:`` scan), since most of
    a scaffold's field surface is commented out.
    """
    config_cls = CONFIG_REGISTRY[chart_type]
    valid_fields = set(config_cls.model_fields)
    template = get_template(chart_type)

    template_fields = set(yaml.safe_load(template)["chart"])
    template_fields.update(COMMENTED_CHART_FIELD.findall(_chart_section(template)))

    unknown = template_fields - valid_fields
    assert not unknown, (
        f"{chart_type} template mentions fields not on {config_cls.__name__}: {sorted(unknown)}"
    )
